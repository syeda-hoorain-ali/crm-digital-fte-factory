# Step 2: Map Prototype Code to Production Components

**Phase**: Custom Agent Transition - Production Structure Setup
**Created**: 2026-02-23
**Reference**: Hackathon Guide Step 2 - Code Mapping

## Overview

This tasks file covers Step 2 of the transition from incubation (Claude Code + MCP) to production (OpenAI Agents SDK + FastAPI + PostgreSQL). The goal is to create the production folder structure and migrate the working incubation code to production components.

**Current Scope (MVP):**
- ✅ Migrate from Claude Code (general agent) to OpenAI Agents SDK (custom agent)
- ✅ Convert MCP server tools to @function_tools
- ✅ Migrate from file storage to PostgreSQL database
- ✅ Add embedding + vector search + alembic migration

**Out of Scope (Future):**
- ❌ Kafka integration (will use direct API calls for now)
- ❌ Channel integrations (Gmail, WhatsApp, Web Form - will test via API endpoint)

## Code Mapping Reference

```
INCUBATION (What we built)             PRODUCTION (Where it goes)
───────────────────────────            ───────────────────────────

mcp-server/src/tools.py          →     backend/src/agent/tools/*.py
mcp-server/src/storage/          →     backend/src/database/
mcp-server/context/              →     PostgreSQL knowledge_base table
Skills (5 skills)                →     backend/src/agent/customer_success_agent.py
MCP server tools (7 tools)       →     @function_tool decorated functions
File-based storage               →     PostgreSQL + async connection pool
TF-IDF search                    →     pgvector semantic search
Manual testing                   →     pytest test suite
Hardcoded config                 →     Environment variables
```

---

## Tasks

### 1. Dependencies & Configuration Setup

#### 1.1 Install Dependencies
- [ ] Install core dependencies: `uv add fastapi uvicorn pydantic pydantic-settings`
- [ ] Install database dependencies: `uv add asyncpg alembic psycopg2-binary pgvector`
- [ ] Install OpenAI dependencies: `uv add openai-agents`
- [ ] Install embedding dependencies: `uv add fastembed`
- [ ] Install testing dependencies: `uv add --dev pytest pytest-asyncio httpx`
- [ ] Install utilities: `uv add python-dotenv vaderSentiment`

**Acceptance Criteria**:
- All dependencies installed successfully
- `uv.lock` file updated
- No version conflicts

#### 1.2 Initialize Alembic
- [ ] Run `alembic init -t async alembic` (if not already done)
- [ ] Verify alembic directory structure created
- [ ] Update `alembic.ini` with correct database URL placeholder

**Acceptance Criteria**:
- Alembic initialized with async template
- Directory structure: `alembic/versions/`, `alembic/env.py`, `alembic.ini`

#### 1.3 Create Configuration Files
- [ ] Update `backend/.env.example` with all required variables
- [ ] Create `backend/src/config.py` with Pydantic settings
- [ ] Add DATABASE_URL configuration
- [ ] Add OPENAI_API_KEY configuration
- [ ] Add embedding model configuration
- [ ] Validate all required config on startup

**Acceptance Criteria**:
- `.env.example` has all variables documented
- `config.py` uses Pydantic BaseSettings
- Missing config causes startup failure with clear error
- Config validation works

---

### 2. Database Schema Setup

#### 2.1 Create Database Models
- [ ] Create `backend/src/database/__init__.py`
- [ ] Create `backend/src/database/models.py` with SQLAlchemy models
- [ ] Define `Customer` model (id, email, phone, metadata, created_at)
- [ ] Define `Ticket` model (id, ticket_id, customer_id, issue, priority, channel, status, created_at)
- [ ] Define `Message` model (id, ticket_id, direction, content, channel, sentiment_score, created_at)
- [ ] Define `Escalation` model (id, ticket_id, triggered_criteria, priority, reason, created_at)
- [ ] Define `KnowledgeBase` model (id, title, content, category, embedding vector, created_at)
- [ ] Define `Response` model (id, ticket_id, content, channel_formatted, delivery_status, created_at)

**Acceptance Criteria**:
- All models use SQLAlchemy declarative base
- All tables have proper indexes
- Foreign key relationships defined
- Timestamps use UTC
- KnowledgeBase has vector column for pgvector

#### 2.2 Create Alembic Migrations
- [ ] Import models in `alembic/env.py`
- [ ] Create initial migration: `alembic revision --autogenerate -m "initial schema"`
- [ ] Add pgvector extension to migration
- [ ] Add vector indexes for similarity search
- [ ] Test migration up: `alembic upgrade head`
- [ ] Test migration down: `alembic downgrade -1`

**Acceptance Criteria**:
- Migrations run successfully
- Rollback works correctly
- pgvector extension enabled
- Vector indexes created

#### 2.3 Create Database Connection Layer
- [ ] Create `backend/src/database/connection.py` with async connection pool
- [ ] Create `backend/src/database/queries.py` with CRUD operations
- [ ] Implement customer CRUD operations
- [ ] Implement ticket CRUD operations
- [ ] Implement message CRUD operations
- [ ] Implement escalation CRUD operations
- [ ] Implement knowledge base search with pgvector similarity
- [ ] Implement response CRUD operations

**Acceptance Criteria**:
- Connection pool uses asyncpg
- All queries are parameterized (SQL injection safe)
- Error handling with retries
- Connection pool configuration from environment variables
- Vector similarity search working

#### 2.4 Migrate Knowledge Base Content
- [ ] Create `backend/scripts/migrate_knowledge_base.py`
- [ ] Load markdown files from `mcp-server/context/`
- [ ] Generate embeddings using sentence-transformers
- [ ] Insert articles into `knowledge_base` table with embeddings
- [ ] Verify search functionality with pgvector
- [ ] Test similarity search returns relevant results

**Acceptance Criteria**:
- All markdown files from `mcp-server/context/` migrated
- Embeddings generated and stored as vectors
- Search returns relevant results ordered by similarity
- Script is idempotent (can run multiple times safely)

---

### 3. Agent Module Setup

#### 3.1 Create Agent Core Files
- [ ] Create `backend/src/agent/__init__.py` with module exports
- [ ] Create `backend/src/agent/tools/__init__.py` with module exports
- [ ] Create `backend/src/agent/customer_success_agent.py` skeleton
- [ ] Create `backend/src/agent/prompts.py` with system prompts from incubation
- [ ] Create `backend/src/agent/formatters.py` for channel-specific formatting

**Acceptance Criteria**:
- All files exist and are importable
- No syntax errors
- Module structure matches production requirements

#### 3.2 Extract Working Prompts from Incubation
- [ ] Copy sentiment analysis skill prompt to `prompts.py`
- [ ] Copy customer identification skill prompt to `prompts.py`
- [ ] Copy knowledge retrieval skill prompt to `prompts.py`
- [ ] Copy escalation decision skill prompt to `prompts.py`
- [ ] Copy channel adaptation skill prompt to `prompts.py`
- [ ] Document prompt variables and placeholders

**Acceptance Criteria**:
- All 5 skill prompts extracted verbatim from incubation
- Prompts are stored as Python constants or functions
- Variables are clearly documented

#### 3.3 Convert MCP Tools to @function_tool
- [ ] Create `backend/src/agent/tools/search_knowledge_base.py` with @function_tool
- [ ] Create `backend/src/agent/tools/identify_customer.py` with @function_tool
- [ ] Create `backend/src/agent/tools/create_ticket.py` with @function_tool
- [ ] Create `backend/src/agent/tools/get_customer_history.py` with @function_tool
- [ ] Create `backend/src/agent/tools/escalate_to_human.py` with @function_tool
- [ ] Create `backend/src/agent/tools/send_response.py` with @function_tool
- [ ] Create `backend/src/agent/tools/analyze_sentiment.py` with @function_tool

**Acceptance Criteria**:
- Each tool has its own separate file
- Each tool has proper Pydantic input schema
- Each tool has comprehensive docstring
- Each tool signature matches OpenAI Agents SDK requirements
- Tool descriptions match what worked in incubation
- Tools use database queries instead of file operations

#### 3.4 Implement Customer Success Agent
- [ ] Create agent class using OpenAI Agents SDK
- [ ] Register all 7 @function_tools with the agent
- [ ] Implement agent workflow (sentiment → identification → knowledge → escalation → channel adaptation)
- [ ] Add error handling and logging
- [ ] Test agent execution with sample customer inquiry

**Acceptance Criteria**:
- Agent initializes successfully with all tools
- Agent can execute complete workflow
- Error handling works correctly
- Logging provides visibility into agent decisions

---

### 4. FastAPI Application Setup

#### 4.1 Create Simple Testing API
- [ ] Update `backend/src/main.py` with FastAPI app
- [ ] Add health check endpoint (`GET /health`)
- [ ] Add agent testing endpoint (`POST /agent/process`)
- [ ] Add CORS configuration for local testing
- [ ] Add request/response logging

**Acceptance Criteria**:
- FastAPI app runs successfully with `uvicorn src.main:app --reload`
- Health check returns 200 with status message
- Agent endpoint accepts customer inquiry and returns agent response
- Logging shows request/response details

---

### 5. Testing Setup

#### 5.1 Create Test Structure
- [ ] Create `backend/src/tests/__init__.py`
- [ ] Create `backend/src/tests/conftest.py` with fixtures
- [ ] Create `backend/src/tests/test_agent.py`
- [ ] Create `backend/src/tests/test_tools.py`
- [ ] Create `backend/src/tests/test_database.py`
- [ ] Create `backend/src/tests/test_api.py`

**Acceptance Criteria**:
- Test structure matches production structure
- Fixtures for test database and mocks in place
- Can run `uv run pytest` successfully

#### 5.2 Port Incubation Tests
- [ ] Port tool implementation tests from mcp-server
- [ ] Port customer identification tests
- [ ] Add new tests for database operations
- [ ] Add tests for agent workflow
- [ ] Add API endpoint tests

**Acceptance Criteria**:
- Core functionality tests ported and passing
- New tests for production components added
- Test coverage > 70%

#### 5.3 Create End-to-End Tests
- [ ] Test complete workflow: customer inquiry → agent processing → response
- [ ] Test sentiment analysis → escalation flow
- [ ] Test knowledge base search
- [ ] Test error recovery scenarios

**Acceptance Criteria**:
- E2E tests cover all critical paths
- Tests use test database
- All E2E tests pass

---

### 6. Documentation

#### 6.1 Update Documentation
- [ ] Update `backend/README.md` with setup instructions
- [ ] Document environment variables required
- [ ] Document database setup and migrations
- [ ] Document how to run the agent locally
- [ ] Document testing procedures
- [ ] Add API endpoint documentation

**Acceptance Criteria**:
- README is comprehensive and accurate
- New developers can follow instructions to set up locally
- All commands documented with examples

---

## Validation Checklist

After completing all tasks, verify:

- [ ] All dependencies installed successfully
- [ ] Alembic initialized and configured
- [ ] Configuration management working (config.py + .env)
- [ ] Database schema includes all 6 tables (customers, tickets, messages, escalations, knowledge_base, responses)
- [ ] Alembic migrations run successfully
- [ ] pgvector extension enabled and working
- [ ] Knowledge base migrated with embeddings
- [ ] All 7 MCP tools converted to @function_tool
- [ ] All 5 skill prompts extracted and stored
- [ ] Agent class implemented with OpenAI Agents SDK
- [ ] FastAPI application runs and serves endpoints
- [ ] Health check endpoint working
- [ ] Agent testing endpoint working
- [ ] Tests passing (core functionality)
- [ ] Documentation complete and accurate
- [ ] No hardcoded secrets or credentials
- [ ] All configuration from environment variables

---

## Success Criteria

Step 2 is complete when:

1. **Dependencies**: All required packages installed via uv
2. **Configuration**: Config management working with environment variables
3. **Database**: Schema defined, migrations created, pgvector enabled
4. **Knowledge Base**: Markdown files migrated to PostgreSQL with embeddings
5. **Tools**: All 7 MCP tools converted to @function_tool format
6. **Agent**: Customer Success Agent implemented with OpenAI Agents SDK
7. **API**: FastAPI application running with health check and agent endpoints
8. **Tests**: Test structure in place with core tests passing
9. **Documentation**: README updated with setup and usage instructions
10. **Validation**: Can run agent locally and process customer inquiries end-to-end

---

## Next Steps

After completing Step 2, the agent will be fully functional locally:
- Test the agent with various customer scenarios
- Validate sentiment analysis, escalation logic, and response formatting
- Measure performance and response quality
- Future: Add Kafka for message queuing
- Future: Add channel integrations (Gmail, WhatsApp, Web Form)
- Future: Deploy to Kubernetes for production
