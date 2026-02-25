# Feature Specification: Customer Success Agent Production Migration

**Feature Branch**: `005-custom-agent-transition`
**Created**: 2026-02-23
**Status**: Draft
**Input**: User description: "Migrate Customer Success Agent from incubation (Claude Code + MCP + file storage) to production (OpenAI Agents SDK + PostgreSQL + pgvector)"

## Migration Context

**This is NOT a greenfield project.** We are migrating a working MVP to production infrastructure, not building from scratch.

**What We Already Have (Incubation/MVP)**:
- ✅ Fully functional Customer Success Agent with 67/67 tests passing
- ✅ 5 validated skill prompts (sentiment analysis, customer identification, knowledge retrieval, escalation decision, channel adaptation)
- ✅ 7 working MCP server tools with proven functionality
- ✅ Complete knowledge base with product documentation
- ✅ Tested escalation rules and response patterns
- ✅ End-to-end workflow validated through manual testing

**What We're Changing (Infrastructure Only)**:
- Agent runtime: Claude Code (general agent) → OpenAI Agents SDK (custom agent)
- Tool format: MCP server tools → @function_tool decorators
- Storage: File-based JSON → PostgreSQL with async connection pooling
- Search: TF-IDF keyword search → pgvector semantic search
- Configuration: Hardcoded values → Environment variables
- Testing: Manual testing → Automated pytest suite

**Critical Constraint**: We MUST maintain 100% feature parity with the working MVP. All prompts, tools, escalation rules, and response patterns that work in incubation must be preserved exactly. This is an infrastructure migration, not a feature redesign.

**Success Metric**: The production system should handle the same customer inquiries with the same quality of responses as the incubation MVP, but with production-grade reliability, scalability, and maintainability.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Production-Ready Agent Deployment (Priority: P1)

System operators need to deploy a production-ready Customer Success Agent that can handle real customer inquiries at scale with reliable data persistence and semantic search capabilities.

**Why this priority**: This is the foundation for all other functionality. Without a production-ready deployment infrastructure, the agent cannot serve real customers reliably.

**Independent Test**: Can be fully tested by deploying the agent with database connectivity, processing a sample customer inquiry through the API endpoint, and verifying the conversation and messages are stored in the database with proper observability tracking. Delivers a working agent that can handle basic customer interactions with full data persistence.

**Acceptance Scenarios**:

1. **Given** the agent is deployed with database configuration, **When** a health check is requested, **Then** the system returns healthy status with database connectivity confirmed
2. **Given** the agent receives a customer inquiry via API, **When** the inquiry is processed, **Then** a conversation is created or continued and all interaction data is persisted to the database
3. **Given** the knowledge base is migrated to PostgreSQL, **When** a customer asks a product question, **Then** the agent retrieves relevant documentation using semantic search and provides an accurate answer

---

### User Story 2 - Automated Customer Support Workflow (Priority: P1)

Customers need to receive automated support responses that analyze their sentiment, identify their account, search relevant knowledge, and format responses appropriately for their communication channel.

**Why this priority**: This is the core business value - automating customer support interactions. Without this, the agent provides no customer-facing value.

**Independent Test**: Can be fully tested by sending a customer inquiry with contact information, verifying sentiment analysis runs, customer identification succeeds with cross-channel matching, conversation is created or continued, knowledge base search returns relevant results, and a properly formatted response is stored as a message with role="agent". Delivers end-to-end customer support automation with cross-channel customer unification.

**Acceptance Scenarios**:

1. **Given** a customer sends an inquiry with email/phone, **When** the agent processes the message, **Then** the customer is identified or created via CustomerIdentifier lookup and their conversation history is retrieved across all channels
2. **Given** a customer contacts via different channel (e.g., email then WhatsApp), **When** identified, **Then** system unifies customer record and retrieves full conversation history across all channels
3. **Given** a customer inquiry contains frustrated language, **When** sentiment analysis runs, **Then** the sentiment score is calculated and stored with the message
4. **Given** a customer asks about product features, **When** the agent searches the knowledge base, **Then** relevant articles are retrieved using vector similarity search and included in the response
5. **Given** a response is generated for a specific channel, **When** the response is formatted, **Then** it follows channel-specific style guidelines (formal for email, casual for chat) and is stored as a message with role="agent"

---

### User Story 3 - Escalation Management (Priority: P2)

Support teams need the agent to automatically escalate complex or high-priority customer issues to human agents based on sentiment trends, conversation context, and business-specific triggers.

**Why this priority**: While automated responses handle most inquiries, human escalation is critical for customer satisfaction in complex cases. This is P2 because basic agent functionality must work first.

**Independent Test**: Can be fully tested by sending inquiries that trigger escalation criteria (negative sentiment, explicit escalation requests, high-value accounts), verifying conversation.escalated_to field is updated with correct priority and reason, and confirming conversation.status changes to "escalated". Delivers intelligent escalation routing via conversation lifecycle tracking.

**Acceptance Scenarios**:

1. **Given** a customer's sentiment score drops below threshold, **When** the escalation decision runs, **Then** the conversation.escalated_to field is set and conversation.status changes to "escalated" with reason stored in metadata
2. **Given** a customer explicitly requests human support, **When** the agent processes the request, **Then** the conversation is immediately escalated with high priority via conversation lifecycle fields
3. **Given** a high-value customer account is identified, **When** any issue is reported, **Then** the escalation criteria are adjusted to prioritize human review and update conversation.escalated_to accordingly

---

### User Story 4 - System Testing and Maintenance (Priority: P2)

Developers need comprehensive test coverage and clear configuration management to maintain and evolve the agent system reliably.

**Why this priority**: Testing and maintainability are essential for long-term success but can be implemented after core functionality is working. This is P2 because the agent must work before it can be tested comprehensively.

**Independent Test**: Can be fully tested by running the test suite, verifying all core functionality tests pass, checking test coverage metrics, and confirming configuration can be updated via environment variables without code changes. Delivers maintainable, testable system.

**Acceptance Scenarios**:

1. **Given** the test suite is executed, **When** all tests run, **Then** core functionality tests pass with >70% code coverage
2. **Given** configuration needs to be updated, **When** environment variables are changed, **Then** the agent picks up new configuration without code modifications
3. **Given** database schema changes are needed, **When** Alembic migrations are run, **Then** schema updates apply successfully with rollback capability

---

### Edge Cases

- What happens when the database connection fails during agent processing?
- How does the system handle customer inquiries when the knowledge base is empty or returns no results?
- What happens when sentiment analysis fails or returns ambiguous scores?
- How does the agent behave when a customer provides invalid or incomplete contact information?
- What happens when vector similarity search returns no relevant results above the threshold?
- How does the system handle concurrent requests to the same customer record?
- What happens when Alembic migrations fail mid-execution?
- How does the agent recover when OpenAI API calls timeout or fail?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST migrate from file-based storage to PostgreSQL database with async connection pooling
- **FR-002**: System MUST convert all MCP server tools to OpenAI Agents SDK @function_tool format
- **FR-003**: System MUST implement semantic search using pgvector for knowledge base queries
- **FR-004**: System MUST persist customer data (email, phone, name, metadata) with cross-channel unification support via CustomerIdentifier table
- **FR-005**: System MUST persist ticket data (category, priority, status, resolved_at, resolution_notes) with conversation relationships
- **FR-006**: System MUST persist message data (content, direction, role, channel, observability fields) with conversation relationships. Observability fields include tokens_used, latency_ms, tool_calls, channel_message_id, delivery_status
- **FR-007**: System MUST track escalation events via conversation lifecycle fields (escalated_to, status) with escalation reason stored in conversation metadata
- **FR-008**: System MUST persist knowledge base articles with vector embeddings (384 dimensions) for similarity search
- **FR-009**: System MUST persist agent responses as messages with role='agent' including channel formatting and delivery status tracking
- **FR-010**: System MUST provide database schema migrations using Alembic with rollback capability
- **FR-011**: System MUST load configuration from environment variables (database URL, API keys, model settings) as defined in .env.example
- **FR-012**: System MUST validate required configuration on startup and fail with clear error messages
- **FR-013**: System MUST expose FastAPI endpoints for health checks and agent processing
- **FR-014**: System MUST implement agent workflow: sentiment analysis → customer identification → knowledge retrieval → escalation decision → channel adaptation
- **FR-015**: System MUST support async database operations for all CRUD functions
- **FR-016**: System MUST parameterize all database queries to prevent SQL injection
- **FR-017**: System MUST implement connection pool error handling with retries and graceful degradation
- **FR-018**: System MUST migrate existing knowledge base markdown files to database with embeddings
- **FR-019**: System MUST extract and preserve all 5 skill prompts from incubation (sentiment analysis, customer identification, knowledge retrieval, escalation decision, channel adaptation)
- **FR-020**: System MUST implement 6 agent tools: search_knowledge_base, identify_customer, create_ticket, get_customer_history, escalate_to_human, send_response
- **FR-021**: System MUST provide comprehensive test coverage (>70%) with pytest test suite
- **FR-022**: System MUST support test database fixtures for isolated testing
- **FR-023**: System MUST log agent decisions and tool executions for observability using structured JSON logs with correlation IDs
- **FR-024**: System MUST support cross-channel customer unification via CustomerIdentifier table enabling same customer recognition across email, phone, and WhatsApp
- **FR-025**: System MUST track conversation lifecycle with status (active, resolved, escalated, closed), sentiment_score, started_at, ended_at, and escalated_to fields
- **FR-026**: System MUST support channel-specific configuration via ChannelConfig table including enabled status, API credentials, response templates, and max response length
- **FR-027**: System MUST track agent performance metrics via AgentMetric table including metric name, value, channel, and dimensions for cost tracking and performance monitoring
- **FR-028**: System MUST handle database connection failures with retry logic and graceful degradation to prevent request failures
- **FR-029**: System MUST implement optimistic locking or row-level locking for concurrent customer record updates to prevent data corruption
- **FR-030**: System MUST implement custom PostgreSQL-backed session following SessionABC protocol using Message table for conversation memory persistence across multiple agent runs
- **FR-031**: System MUST support async session operations (get_items, add_items, pop_item, clear_session) for conversation history management using Message table as storage
- **FR-032**: System MUST isolate sessions by conversation_id to maintain independent conversation histories for multi-user support
- **FR-033**: System MUST transform Message records to EasyInputMessageParam format in get_items() by mapping: content→content, role(customer→user, agent→assistant, system→system), phase(agent→final_answer, user→None), type→"message"
- **FR-034**: System MUST transform EasyInputMessageParam items to Message records in add_items() by extracting content and role, deriving business role from SDK role
- **FR-035**: System MUST implement clear_session() as no-op (pass) to preserve all message data for audit trail and business records. To start fresh conversation, create new Conversation with new conversation_id instead of clearing existing session.
- **FR-036**: System MUST implement RunHooks with lifecycle methods (on_agent_start, on_agent_end, on_tool_start, on_tool_end, on_handoff) for observability
- **FR-037**: System MUST use trace() context manager to group related agent runs into logical workflows with workflow_name and group_id
- **FR-038**: System MUST link multi-turn conversations using group_id in trace() to enable conversation-level analysis in OpenAI dashboard
- **FR-039**: System MUST track token usage from result.raw_responses for cost monitoring and populate AgentMetric table with usage data
- **FR-040**: System MUST implement custom_span() for sub-operations within traces to create hierarchical observability structure
- **FR-041**: System MUST log all lifecycle events (agent start/end, tool calls, handoffs) as structured JSON with timestamps and correlation IDs
- **FR-042**: System MUST populate AgentMetric table via RunHooks with metrics including tokens_used, latency_ms, tool_call_count, and estimated_cost

### Key Entities

- **Customer**: Represents a unified customer across all communication channels with contact information (email, phone, name), metadata, and timestamps. Uniquely identified across all interactions with support for cross-channel unification.
- **CustomerIdentifier**: Tracks customer identifiers across different channels (email, phone, WhatsApp) for cross-channel matching and unification. Enables same customer to be recognized across multiple contact methods.
- **Conversation**: Represents a conversation session with lifecycle tracking (started_at, ended_at, status, sentiment_score). Primary entity for message grouping. Tracks escalation state (escalated_to field) and resolution type. Conversations span multiple channels and can have multiple linked tickets.
- **Message**: Represents a single message in a conversation with content, direction (inbound/outbound), role (customer/agent/system), channel, and observability fields (tokens_used, latency_ms, tool_calls). Messages belong to conversations, not tickets. Agent responses stored as messages with role="agent".
- **Ticket**: Represents a customer support ticket linked to a conversation with category, priority level, status, and resolution tracking (resolved_at, resolution_notes). Multiple tickets can reference the same conversation for support workflow tracking.
- **KnowledgeBase**: Represents a knowledge base article with title, content, category, and vector embedding (384 dimensions). Enables semantic search for relevant documentation using pgvector.
- **ChannelConfig**: Stores channel-specific configuration (enabled status, API keys, response templates, max response length) for multi-channel support (email, WhatsApp, web form, API).
- **AgentMetric**: Tracks agent performance metrics (metric name, value, channel, dimensions) for observability and analytics. Enables monitoring of agent behavior, cost tracking, and performance optimization.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Agent can process customer inquiries end-to-end (sentiment → identification → knowledge → escalation → response) in under 5 seconds, measured from API request receipt to response return including all database operations and tool executions
- **SC-002**: Database schema migrations run successfully with zero data loss and rollback capability
- **SC-003**: Knowledge base semantic search returns relevant results with >80% accuracy compared to keyword search baseline, measured by human evaluation of top-5 results for 50 test queries comparing pgvector semantic search vs TF-IDF baseline
- **SC-004**: All 7 agent tools execute successfully with proper error handling and logging
- **SC-005**: Test suite achieves >70% code coverage with all core functionality tests passing
- **SC-006**: System handles concurrent requests without database connection pool exhaustion
- **SC-007**: Agent maintains 100% parity with incubation functionality (all 5 skills, all 6 tools, all escalation rules)
- **SC-008**: Configuration changes can be applied via environment variables without code modifications
- **SC-009**: FastAPI health check endpoint responds within 100ms confirming database connectivity
- **SC-010**: Agent processing endpoint accepts customer inquiries and returns formatted responses via REST API with conversation_id for history retrieval

## Assumptions

- PostgreSQL database is available and accessible via connection string
- OpenAI API access is available with valid API key
- Existing knowledge base markdown files are accessible for migration
- Incubation code (MCP server, skills) is available for reference
- Development environment has Python 3.12+ and uv package manager
- Database supports pgvector extension for vector similarity search
- Test environment can use isolated test database for fixtures
- Alembic migrations will be run manually during deployment (auto-applied in production using ci/cd pipeline)

## Out of Scope

- Kafka integration for message queuing (future enhancement)
- Channel integrations (Gmail, WhatsApp, Web Form) - will test via API endpoint only
- Production deployment infrastructure (Kubernetes, Docker orchestration)
- Monitoring and alerting setup (Prometheus, Grafana)
- Load balancing and horizontal scaling
- Authentication and authorization for API endpoints
- Rate limiting and API throttling
- Backup and disaster recovery procedures
- Multi-tenancy support
- Real-time WebSocket connections for live chat

## Dependencies

- PostgreSQL database with pgvector extension
- OpenAI API access for agent execution
- Existing incubation codebase (mcp-server, skills) for migration reference
- Python 3.12+ runtime environment
- uv package manager for dependency management
