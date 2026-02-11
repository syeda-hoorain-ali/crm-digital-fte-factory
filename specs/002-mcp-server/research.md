# Research: MCP Server for CRM Digital FTE Factory

## MCP SDK Investigation

### Decision: Use fastmcp as the MCP server framework
**Rationale**: The example server template in `.claude/skills/mcp-server-creator/assets/templates/custom/example_server.py` demonstrates using fastmcp as the preferred approach. It's designed for the official MCP SDK and follows the recommended patterns.

**Alternatives considered**:
- Raw MCP SDK: Would require more boilerplate code
- Custom implementation: Would not follow MCP specification properly

## Tool Mapping from Existing CRM Tools

### Decision: Map existing CRM tools to MCP server functions
**Rationale**: The existing `backend/src/agent/tools/crm_tools.py` already implements core functionality that aligns with the required MCP tools:
- `search_product_docs` → `search_knowledge_base`
- `create_support_ticket` → `create_ticket`
- `lookup_customer` + historical data → `get_customer_history`
- `escalate_ticket` → `escalate_to_human`
- `save_reply_to_file` → basis for `send_response`

**Alternatives considered**:
- Rewrite from scratch: Would duplicate existing functionality
- Separate implementation: Would create inconsistency with existing tools

## Security Implementation Strategy

### Decision: Implement authentication and rate limiting
**Rationale**: The existing CRM system handles sensitive customer data and must be secured. The MCP architecture document shows patterns for authentication and rate limiting.

**Alternatives considered**:
- No security: Would expose customer data and system to risks
- Basic security: Would not meet enterprise requirements

## MCP Tool Specifications

### Decision: Follow MCP specification for all 5 required tools
**Rationale**: The hackathon documentation specifically defines these 5 tools with their signatures and return values. Following the specification ensures compatibility with Claude and other MCP clients.

**Required Tools**:
1. `search_knowledge_base(query)` → returns relevant docs
2. `create_ticket(customer_id, issue, priority, channel)` → returns ticket_id
3. `get_customer_history(customer_id)` → returns past interactions
4. `escalate_to_human(ticket_id, reason)` → returns escalation_id
5. `send_response(ticket_id, message, channel)` → returns delivery_status

## Implementation Approach

### Decision: Extend existing CRM tools with MCP wrapper
**Rationale**: Rather than duplicating functionality, create an MCP server that wraps the existing CRM tools. This maintains consistency and reduces maintenance overhead.

**Steps**:
1. Create MCP server with fastmcp
2. Adapt existing CRM tool functions to MCP tool signatures
3. Add security and validation layers
4. Implement health checks and monitoring
