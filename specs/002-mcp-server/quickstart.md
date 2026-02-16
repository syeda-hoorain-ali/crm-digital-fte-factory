# Quickstart Guide: MCP Server for CRM Digital FTE Factory

## Prerequisites

- Python 3.11+
- Poetry (dependency manager)
- Network access to connect to Claude or other MCP clients

## Setup

### 1. Install Dependencies

```bash
cd mcp-server
uv sync
```

### 2. Set Environment Variables

Create a `.env` file in the mcp-server directory:

```env
MCP_SERVER_TOKEN=your-secret-token-here
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

### 1. Configure Claude to connect to the MCP server:

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

### 2. Start Claude and use the MCP tools:

The following tools will be available:
- `search_knowledge_base(query)`
- `create_ticket(customer_id, issue, priority, channel)`
- `get_customer_history(customer_id)`
- `escalate_to_human(ticket_id, reason)`
- `send_response(ticket_id, message, channel)`

## Testing the Server

### Unit Tests

```bash
cd mcp-server
uv run pytest
```

### Manual Testing

1. Start the server: `uv run -m src/main.py`
2. Connect an MCP client to test the tools
3. Verify each tool returns expected results

## Health Check

The server provides a health check endpoint at `/health` when running in HTTP mode:

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-10T19:30:00.123456",
  "service": "crm-digital-fte-mcp-server",
  "version": "1.0.0"
}
```

## Troubleshooting

### Server Won't Start
- Check that all dependencies are installed
- Verify environment variables are set correctly
- Ensure no other process is using the same port

### Tools Not Working
- Verify authentication token is correct
- Check that the server is running and connected
- Review server logs for error messages

### Authentication Issues
- Confirm MCP_SERVER_TOKEN matches between client and server
- Verify environment variable is properly loaded
- Check server logs for authentication failure messages
