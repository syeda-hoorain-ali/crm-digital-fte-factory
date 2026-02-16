---
name: openai-mcp-connector
description: Connect Model Context Protocol (MCP) servers with OpenAI Agents SDK using various transport methods including Hosted MCP, Streamable HTTP, HTTP with SSE, and stdio. Provides guidance for selecting appropriate transport methods, configuring connections with proper authentication, implementing error handling, and following best practices for security and performance. Use when connecting MCP servers to AI applications, configuring transport protocols, setting up authentication, or troubleshooting connection issues.
---

# OpenAI MCP Connector

Connect Model Context Protocol (MCP) servers with OpenAI Agents SDK using various transport methods. This skill provides guidance for selecting appropriate transport methods, configuring connections with proper authentication, implementing error handling, and following best practices for security and performance.

## Overview

Model Context Protocol (MCP) acts as a standardized way for applications to provide context to LLMs - think of it as a "USB-C port for AI applications". This skill helps you connect MCP servers to OpenAI Agents SDK using different transport mechanisms.

## Transport Methods

### 1. Hosted MCP Server
Use when connecting to publicly accessible MCP servers through OpenAI's infrastructure.

Key features:
- Support for direct server URLs and OpenAI connector IDs (like "connector_gmail", "connector_googledrive")
- Authentication via OAuth tokens and custom headers
- Approval mechanisms for sensitive operations using `on_approval_request` functions
- Configuration options for requiring approval always/never or per-tool basis

### 2. Streamable HTTP MCP Server
Use when managing HTTP connections directly, running local/remote servers, or maintaining low-latency infrastructure.

Key features:
- HTTP connection parameter configuration with authentication headers
- Timeout controls for requests and SSE connections
- Caching capabilities for available tools
- Retry mechanisms with exponential backoff
- Direct server connection management

### 3. HTTP with Server-Sent Events (SSE)
Use for real-time event streaming from MCP servers using SSE transport.

Key features:
- Configurable connection parameters and headers
- Timeout settings for HTTP requests and SSE connections
- Tool caching capabilities
- Retry mechanisms with exponential backoff
- Support for structured content and message handling

### 4. Stdio MCP Server
Use for local development environments and command-line server implementations.

Key features:
- Local MCP server subprocess communication through standard input/output
- Configurable process parameters including command, arguments, environment variables, and working directory
- Encoding settings and structured content handling
- Process management and communication handling

## Connection Framework

When deciding which transport method to use, consider:

- **Execution Location**: Local development vs. cloud deployment
- **Network Accessibility**: Public vs. private/internal access
- **Performance Requirements**: Real-time vs. batch processing
- **Security Constraints**: Authentication and authorization needs
- **Infrastructure Limitations**: Available protocols and services

## Troubleshooting

Common issues include:
- Connection failures
- Authentication errors
- Tool discovery issues
- Communication errors
- Performance problems
- Configuration issues

See references/troubleshooting.md for detailed diagnostic procedures and solutions.

## Best Practices

- Always implement proper error handling and retry mechanisms
- Use appropriate authentication for each transport method
- Enable caching when dealing with frequently accessed tools
- Configure timeouts based on expected response times
- Follow security best practices for token management
- Monitor performance and adjust connection parameters accordingly

## References

For detailed implementation guides, configuration options, and examples, see the reference files:
- [references/hosted-mcp.md](references/hosted-mcp.md) - Hosted MCP server connections
- [references/streamable-http-mcp.md](references/streamable-http-mcp.md) - Streamable HTTP connections
- [references/sse-mcp.md](references/sse-mcp.md) - Server-Sent Events connections
- [references/stdio-mcp.md](references/stdio-mcp.md) - Stdio connections
- [references/troubleshooting.md](references/troubleshooting.md) - Diagnostic procedures and solutions
