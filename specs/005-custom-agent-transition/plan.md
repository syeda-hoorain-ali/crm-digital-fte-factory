# Implementation Plan: Customer Success Agent Production Migration

**Branch**: `005-custom-agent-transition` | **Date**: 2026-02-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-custom-agent-transition/spec.md`

**Note**: This template is filled in by the `/sp.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Migrate a working Customer Success Agent MVP (67/67 tests passing) from incubation infrastructure (Claude Code + MCP + file storage) to production infrastructure (OpenAI Agents SDK + PostgreSQL + pgvector). This is an infrastructure-only migration that MUST maintain 100% feature parity with the working MVP. The migration converts 7 MCP server tools to @function_tool decorators, migrates file-based storage to PostgreSQL with async connection pooling, replaces TF-IDF search with pgvector semantic search using FastEmbed embeddings, and implements automated pytest test suite.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**:
- FastAPI (web framework)
- OpenAI Agents SDK (agent runtime)
- SQLModel (ORM with Pydantic validation)
- asyncpg (async PostgreSQL driver)
- Alembic (database migrations)
- FastEmbed (local embeddings)
- pgvector (vector similarity search)
- pytest + pytest-asyncio (testing)
- python-dotenv (configuration)
- vaderSentiment (sentiment analysis)

**Storage**: PostgreSQL (Neon Serverless) with pgvector extension for vector embeddings
**Testing**: pytest with pytest-asyncio, Neon test database for integration tests
**Target Platform**: Linux server (FastAPI + uvicorn)
**Project Type**: Web application (backend API only, no frontend in this phase)
**Performance Goals**:
- Agent processing: <5 seconds end-to-end
- Health check: <100ms response time
- Database queries: <200ms p95 latency
- Vector similarity search: <500ms for top-k retrieval

**Constraints**:
- 100% feature parity with incubation MVP (non-negotiable)
- All 5 skill prompts must be preserved exactly
- All 6 tools must maintain identical behavior (with schema updates)
- All escalation rules must work identically
- >70% test coverage required
- Zero data loss during knowledge base migration

**Scale/Scope**:
- 7 agent tools to migrate (behavior preserved, schema updated)
- 5 skill prompts to extract
- 8 database entities (Customer, CustomerIdentifier, Conversation, Message, Ticket, KnowledgeBase, ChannelConfig, AgentMetric)
- ~50-100 knowledge base articles to migrate with embeddings
- Target: 1000 concurrent requests without pool exhaustion
- Cross-channel customer unification via CustomerIdentifier table
- Conversation-centric design with full observability tracking

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Compliance Status

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Python-First Backend** | ✅ PASS | All backend code in Python 3.12+ with FastAPI |
| **II. MCP Standard** | ⚠️ MIGRATION | Migrating FROM MCP to @function_tools (intentional departure for production) |
| **III. React Frontend** | ✅ N/A | No frontend in this phase (API only) |
| **IV. Pytest Testing** | ✅ PASS | Pytest with pytest-asyncio, >70% coverage target |
| **V. SQL-First Data Modeling** | ✅ PASS | PostgreSQL with SQLModel, Alembic migrations, normalized schema |
| **VI. UV Package Management** | ✅ PASS | UV for all Python dependencies |

### ⚠️ MCP Departure Justification

**Violation**: Migrating away from MCP server tools to OpenAI Agents SDK @function_tools

**Why Needed**:
- OpenAI Agents SDK provides native agent runtime with better performance and observability
- @function_tools integrate directly with agent execution without MCP transport overhead
- Production deployment requires custom agent with direct database access, not general agent with MCP
- MCP was appropriate for incubation/prototyping, but production needs tighter integration

**Simpler Alternative Rejected**:
- Keeping MCP would require maintaining MCP server + agent runtime + transport layer
- MCP adds latency and complexity for production deployment
- Direct @function_tools provide better error handling and type safety

**Mitigation**:
- All tool functionality preserved exactly (100% feature parity)
- Tool behavior validated through comprehensive test suite
- Migration path documented for future MCP reintegration if needed

## Project Structure

### Documentation (this feature)

```text
specs/005-custom-agent-transition/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command)
│   └── api.yaml         # OpenAPI specification for FastAPI endpoints
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── customer_success_agent.py    # Main agent with OpenAI Agents SDK
│   │   ├── prompts.py                   # 5 skill prompts from incubation
│   │   ├── formatters.py                # Channel-specific formatting
│   │   ├── session.py                   # Custom PostgreSQL session (SessionABC)
│   │   ├── hooks.py                     # RunHooks for observability
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── search_knowledge_base.py # @function_tool
│   │       ├── identify_customer.py     # @function_tool
│   │       ├── analyze_sentiment.py     # @function_tool
│   │       ├── create_ticket.py         # @function_tool
│   │       ├── get_customer_history.py  # @function_tool
│   │       ├── escalate_to_human.py     # @function_tool
│   │       └── send_response.py         # @function_tool
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py                # Async engine + session management
│   │   ├── models.py                    # SQLModel table definitions
│   │   └── queries.py                   # CRUD operations
│   ├── config.py                        # Pydantic Settings for env vars
│   └── main.py                          # FastAPI app with endpoints
├── scripts/
│   └── migrate_knowledge_base.py        # One-time migration script
├── alembic/
│   ├── versions/                        # Migration files
│   └── env.py                           # Alembic configuration
├── tests/
│   ├── conftest.py                      # Shared fixtures
│   ├── unit/
│   │   ├── test_tools.py                # Tool logic with mocked database
│   │   ├── test_session_logic.py        # Session transformations (Message ↔ EasyInputMessageParam)
│   │   ├── test_hooks_logic.py          # Hook callbacks with mocked context
│   │   ├── test_formatters.py           # Channel formatting logic
│   │   └── test_prompts.py              # Prompt template rendering
│   └── integration/
│       ├── test_database_crud.py        # Real database operations
│       ├── test_session_persistence.py  # Session operations with real Message table
│       ├── test_agent_workflow.py       # Full agent runs with real database
│       ├── test_api_endpoints.py        # FastAPI endpoints with real database
│       └── test_knowledge_migration.py  # Knowledge base migration script
├── pyproject.toml                       # UV dependencies
├── .env.example                         # Environment variable template
└── README.md                            # Setup and usage instructions
```

**Structure Decision**: Web application structure with backend/ directory. No frontend in this phase. Agent module contains OpenAI Agents SDK implementation with @function_tools, custom PostgreSQL session (SessionABC), and RunHooks for observability. Database module handles PostgreSQL with SQLModel. Scripts directory for one-time knowledge base migration. Tests organized into unit/ (fast, mocked) and integration/ (real database) subdirectories for optimal CI/CD performance.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| MCP Standard departure | Production requires custom agent with direct database access and lower latency | MCP server adds transport overhead, complexity, and latency unsuitable for production. Direct @function_tools provide better performance and error handling. |

---

## Phase 0: Research & Technology Decisions

### Research Questions

1. **FastEmbed Integration**: How to generate and store embeddings using FastEmbed (sentence-transformers)?
2. **pgvector Setup**: How to configure pgvector extension in Neon PostgreSQL?
3. **Async Database Patterns**: Best practices for async SQLModel with asyncpg connection pooling?
4. **OpenAI Agents SDK Context**: How to design Pydantic context model for agent state management?
5. **Tool Migration**: Pattern for converting MCP tools to @function_tool decorators?
6. **Knowledge Base Migration**: Strategy for one-time migration of markdown files to PostgreSQL with embeddings?
7. **Test Database Strategy**: How to configure Neon test database for CI/CD with branch creation?
8. **Alembic Async Migrations**: How to set up Alembic with async template for SQLModel?
9. **Custom Session Implementation**: How to implement SessionABC protocol using Message table as storage backend?
10. **Tracing and Hooks**: How to implement RunHooks for lifecycle observability and populate AgentMetric table?
11. **Token Usage Tracking**: How to extract token usage from result.raw_responses and calculate costs?

### Technology Decisions (from user clarifications)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Embedding Model** | FastEmbed (sentence-transformers) | Free, runs locally, no API dependency, acceptable accuracy for knowledge base search |
| **Knowledge Base Migration** | One-time setup script | Clean separation, manual control, will add dashboard later for ongoing updates |
| **Test Database** | Neon test database | Tests pgvector functionality, validates production behavior, CI/CD creates branches per PR |
| **Agent Context** | Pydantic BaseModel with conversation history | Tracks customer, ticket, sentiment, escalation, knowledge articles, and full conversation history |
| **Tool Priority** | P0 first (3 tools), then P1 (4 tools) | Validate core workflow before implementing full feature set |
| **Configuration** | .env file with Pydantic BaseSettings | Simple, type-safe, follows FastAPI best practices |
| **Session Backend** | Custom PostgreSQL implementation using Message table | Reuses existing Message table for dual purpose (business data + session memory), no additional storage needed, follows SessionABC protocol |
| **Session Item Format** | EasyInputMessageParam | Simple 4-field format (role, content, phase, type) constructed from existing Message fields without additional storage |
| **Session Isolation** | conversation_id as session_id | Natural isolation boundary, aligns with business model, enables multi-user support |
| **Tracing Strategy** | OpenAI Agents SDK trace() + RunHooks | Built-in tracing to OpenAI dashboard with custom hooks for AgentMetric population and structured logging |
| **Observability Hooks** | Custom RunHooks implementation | Lifecycle callbacks (on_agent_start, on_agent_end, on_tool_start, on_tool_end, on_handoff) for metrics collection and logging |
| **Token Tracking** | Extract from result.raw_responses | Access usage data from SDK responses, calculate costs, populate AgentMetric table via hooks |

### Database Strategy (CI/CD)

**Local Development:**
- Dev & test database same (for MVP simplicity)
- Connection string from .env file

**CI/CD for Pull Requests:**
```
PR opened → Neon creates test branch from main (via API)
         → Apply Alembic migrations to test branch
         → Run pytest against test branch
         → Tests pass → Delete test branch
         → Tests fail → Keep branch for debugging
```

**CI/CD for Main (Production):**
```
PR merged → Apply Alembic migrations to main Neon database
         → Deploy backend to production
         → Health check validates deployment
```

**Migration Safety:**
- All migrations tested in branch before merging
- Alembic downgrade migrations for rollback capability
- Schema drift detection in CI (fail if local != database)
- Neon branch naming: `test-pr-{number}` for traceability
