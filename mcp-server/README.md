# CRM Digital FTE Factory - MCP Server

A lightweight, file-based Model Context Protocol (MCP) server for the CRM Digital FTE Factory project. This server exposes customer support functionality through standardized MCP tools that can be used by AI agents.

## Overview

This MCP server provides a **file-based storage architecture** designed for local development and MVP testing without requiring database infrastructure. All data is stored in simple, human-readable formats (JSON, Markdown, Text files).

### Available Tools

- `search_knowledge_base(query, max_results)` - Search product documentation using TF-IDF
- `identify_customer(email, phone)` - Identify or create customers from contact info
- `create_ticket(customer_id, issue, priority, channel)` - Create support tickets
- `get_customer_history(customer_id)` - Retrieve customer interaction history
- `escalate_to_human(ticket_id, reason)` - Escalate tickets to human support
- `send_response(ticket_id, message, channel)` - Send responses to customers
- `analyze_sentiment(message_text)` - Analyze sentiment of customer messages

## Architecture

### File-Based Storage

- **Knowledge Base**: Markdown files in `context/*.md` with TF-IDF search
- **Tickets**: JSON file at `context/sample-tickets.json` with auto-incrementing IDs
- **Replies**: Text files in `replies/*.txt` for agent responses
- **Customers**: Extracted from ticket data (no separate customer database)

### Key Features

- ✅ **No Database Required**: All data stored in files
- ✅ **Human-Readable**: JSON, Markdown, and Text formats
- ✅ **TF-IDF Search**: Fast semantic search without embeddings
- ✅ **Auto-Incrementing IDs**: Tickets get sequential IDs (TKT-001, TKT-002, etc.)
- ✅ **Sentiment Analysis**: VADER sentiment analysis for customer messages
- ✅ **Comprehensive Testing**: 67 tests covering all tools and workflows

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

Create a `.env` file in the mcp-server directory (optional):

```env
# File storage paths (defaults shown)
CONTEXT_DIR=context
REPLIES_DIR=replies
TICKETS_FILE=context/sample-tickets.json

# Server settings
SERVER_HOST=localhost
SERVER_PORT=8000
LOG_LEVEL=INFO
```

See `.env.example` for all available configuration options.

## Running the Server

### With Claude Code

The server is configured in the root `.mcp.json` file:

```json
{
  "mcpServers": {
    "crm-digital-fte": {
      "type": "stdio",
      "command": "/home/<wsl-username>/.local/bin/uv",
      "args": [
        "run",
        "--frozen",
        "--directory",
        "mcp-server",
        "--with",
        "mcp[cli]",
        "mcp",
        "run",
        "src/main.py"
      ]
    }
  }
}
```

### Development Mode

```bash
cd mcp-server
uv run mcp dev src/main.py
```

This starts the MCP Inspector for interactive testing.

### Direct Execution

```bash
cd mcp-server
uv run -m src.main
```

## Testing

Run all tests:

```bash
cd mcp-server
uv run pytest
```

Run specific test suites:

```bash
# Unit tests only
uv run pytest tests/unit/

# Integration tests only
uv run pytest tests/integration/

# Specific test file
uv run pytest tests/unit/test_tools.py

# With verbose output
uv run pytest -v
```

**Test Coverage**: 67 tests covering:
- 7 tool implementations
- File storage operations
- Customer identification workflows
- End-to-end integration scenarios
- Error handling and edge cases

## Project Structure

```
mcp-server/
├── src/
│   ├── main.py                      # MCP server entry point (FastMCP)
│   ├── config.py                    # Configuration management
│   ├── storage/
│   │   ├── __init__.py              # Storage exports
│   │   └── file_storage.py          # File-based storage layer
│   ├── tools/
│   │   ├── __init__.py              # Tool exports
│   │   ├── analyze_sentiment.py    # Sentiment analysis (VADER)
│   │   ├── create_ticket.py        # Ticket creation
│   │   ├── escalate_to_human.py    # Escalation handling
│   │   ├── get_customer_history.py # Customer lookup
│   │   ├── identify_customer.py    # Customer identification
│   │   ├── search_knowledge_base.py # TF-IDF search
│   │   └── send_response.py        # Response delivery
│   └── utils/
│       └── __init__.py              # Utility exports
├── context/
│   ├── brand-voice.md               # Brand voice guidelines
│   ├── company-profile.md           # Company information
│   ├── escalation-rules.md          # Escalation criteria
│   ├── product-docs.md              # Product documentation
│   └── sample-tickets.json          # Ticket storage (JSON)
├── replies/
│   └── reply_*.txt                  # Agent responses (text files)
├── tests/
│   ├── unit/                        # Unit tests for components
│   ├── integration/                 # End-to-end workflow tests
│   ├── test_customer_identification.py
│   └── conftest.py                  # Shared test fixtures
├── .env.example                     # Example configuration
├── pyproject.toml                   # Project dependencies
└── README.md                        # This file
```

## Storage Layer

### TicketStorage

Manages tickets in `context/sample-tickets.json`:
- Auto-generates sequential IDs (TKT-001, TKT-002, etc.)
- Supports create, read, update operations
- Tracks ticket status and metadata

### KnowledgeBaseStorage

Searches markdown files in `context/`:
- TF-IDF vectorization using scikit-learn
- Returns ranked results with similarity scores
- Supports configurable result limits

### ReplyStorage

Saves agent responses to `replies/`:
- One text file per response
- Filename format: `reply_{ticket_id}_{timestamp}.txt`
- Human-readable for auditing

### CustomerStorage

Extracts customer data from tickets:
- No separate customer database
- Customers identified by email or phone
- History built from ticket interactions

## Dependencies

Core dependencies:
- `fastmcp` - MCP server framework
- `mcp[cli]` - MCP CLI tools
- `scikit-learn` - TF-IDF search
- `vadersentiment` - Sentiment analysis
- `pyyaml` - YAML configuration

Development dependencies:
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support

## Skills Integration

This MCP server is designed to work with the following Claude Code skills:

1. **sentiment-analysis-skill** - Analyzes customer message sentiment
2. **customer-identification** - Identifies customers from contact info
3. **knowledge-retrieval-skill** - Searches product documentation
4. **escalation-decision** - Determines if human escalation is needed
5. **channel-adaptation** - Formats responses for different channels

See the `.claude/skills/` directory for skill implementations.

## Contributing

When adding new tools:
1. Create a new file in `src/tools/`
2. Implement the tool function with proper validation
3. Export from `src/tools/__init__.py`
4. Register in `src/main.py` using `@mcp.tool()`
5. Add tests in `tests/unit/test_tools.py`

## License

See the root project LICENSE file.