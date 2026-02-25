# Tasks: Customer Success Agent Production Migration

**Input**: Design documents from `/specs/005-custom-agent-transition/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.yaml, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Tests**: Tests are NOT included in this task list as they were not explicitly requested in the feature specification. Test implementation is covered in User Story 4.

**Schema Update**: Updated to match hackathon schema with UUID primary keys, conversations table, customer identifiers for cross-channel unification, and full observability tracking.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

This project uses web app structure:
- Backend code: `backend/src/`
- Tests: `backend/tests/`
- Scripts: `backend/scripts/`
- Migrations: `backend/alembic/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency installation

- [ ] T001 Install all Python dependencies using UV in backend/pyproject.toml
- [ ] T002 [P] Create .env.example template in backend/.env.example with all required environment variables
- [ ] T003 [P] Create config.py with Pydantic Settings in backend/src/config.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create all enum types (Priority, Channel, TicketStatus, ConversationStatus, MessageDirection, MessageRole, DeliveryStatus, IdentifierType) in backend/src/database/models.py
- [ ] T005 Create Customer model with UUID PK and name field in backend/src/database/models.py
- [ ] T006 [P] Create CustomerIdentifier model for cross-channel matching in backend/src/database/models.py
- [ ] T007 [P] Create Conversation model with lifecycle tracking in backend/src/database/models.py
- [ ] T008 [P] Create Message model with conversation_id FK and observability fields (role, tokens_used, latency_ms, tool_calls, channel_message_id) in backend/src/database/models.py
- [ ] T009 [P] Create Ticket model with conversation_id FK and resolution tracking in backend/src/database/models.py
- [ ] T010 [P] Create KnowledgeBase model with UUID PK and pgvector support in backend/src/database/models.py
- [ ] T011 [P] Create ChannelConfig model for multi-channel configuration in backend/src/database/models.py
- [ ] T012 [P] Create AgentMetric model for performance tracking in backend/src/database/models.py
- [ ] T013 Create async database engine with connection pooling in backend/src/database/connection.py
- [ ] T014 Create async session management with context manager in backend/src/database/connection.py
- [ ] T015 Add connection retry logic with exponential backoff for database connection failures in backend/src/database/connection.py
- [ ] T016 Add row-level locking for concurrent customer record updates in backend/src/database/queries.py
- [ ] T017 Initialize Alembic with async template in backend/alembic/
- [ ] T018 Configure Alembic env.py to import all SQLModel models in backend/alembic/env.py
- [ ] T019 Generate initial migration with pgvector and uuid-ossp extensions and all 8 tables in backend/alembic/versions/
- [ ] T020 Create CRUD operations for Customer in backend/src/database/queries.py
- [ ] T021 [P] Create CRUD operations for CustomerIdentifier with cross-channel lookup in backend/src/database/queries.py
- [ ] T022 [P] Create CRUD operations for Conversation with lifecycle management in backend/src/database/queries.py
- [ ] T023 [P] Create CRUD operations for Message with conversation history retrieval in backend/src/database/queries.py
- [ ] T024 [P] Create CRUD operations for Ticket with conversation linking in backend/src/database/queries.py
- [ ] T025 [P] Create CRUD operations for KnowledgeBase with vector search in backend/src/database/queries.py
- [ ] T026 [P] Create CRUD operations for ChannelConfig in backend/src/database/queries.py
- [ ] T027 [P] Create CRUD operations for AgentMetric in backend/src/database/queries.py
- [ ] T028 Implement custom PostgreSQL session class following SessionABC protocol in backend/src/agent/session.py
- [ ] T029 Implement get_items() method to query Messages by conversation_id and transform to EasyInputMessageParam in backend/src/agent/session.py
- [ ] T030 Implement add_items() method to insert Messages from EasyInputMessageParam items in backend/src/agent/session.py
- [ ] T031 Implement pop_item() method to delete most recent Message by conversation_id in backend/src/agent/session.py
- [ ] T032 Implement clear_session() as no-op (pass) to preserve message data in backend/src/agent/session.py
- [ ] T033 Implement RunHooks class with lifecycle methods (on_agent_start, on_agent_end, on_tool_start, on_tool_end, on_handoff) in backend/src/agent/hooks.py
- [ ] T034 Add structured JSON logging with timestamps and correlation IDs in RunHooks methods in backend/src/agent/hooks.py
- [ ] T035 Add token usage extraction from result.raw_responses in RunHooks.on_agent_end in backend/src/agent/hooks.py
- [ ] T036 Add AgentMetric population logic in RunHooks.on_agent_end (tokens_used, latency_ms, tool_call_count, estimated_cost) in backend/src/agent/hooks.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Production-Ready Agent Deployment (Priority: P1) 🎯 MVP

**Goal**: Deploy a production-ready Customer Success Agent with database connectivity, semantic search, and basic API endpoints

**Independent Test**: Deploy the agent with database configuration, send a health check request to verify database connectivity, process a sample customer inquiry through POST /agent/process endpoint, and verify the conversation and messages are stored in the database

### Implementation for User Story 1

- [ ] T037 [US1] Create knowledge base migration script with FastEmbed integration in backend/scripts/migrate_knowledge_base.py
- [ ] T038 [US1] Test knowledge base migration script with sample markdown files from mcp-server/context/
- [ ] T039 [US1] Create CustomerSuccessContext Pydantic model with conversation tracking fields in backend/src/agent/customer_success_agent.py
- [ ] T040 [P] [US1] Create FastAPI application with lifespan events in backend/src/main.py
- [ ] T041 [P] [US1] Implement GET /health endpoint with database connectivity check in backend/src/main.py
- [ ] T042 [US1] Create basic Customer Success Agent with OpenAI Agents SDK (name, instructions, model) in backend/src/agent/customer_success_agent.py
- [ ] T043 [US1] Implement POST /agent/process endpoint with request/response models in backend/src/main.py
- [ ] T044 [US1] Integrate agent execution with Runner.run() using custom session and hooks in POST /agent/process endpoint in backend/src/main.py
- [ ] T045 [US1] Wrap agent runs in trace() context manager with group_id for conversation linking in backend/src/main.py
- [ ] T046 [US1] Add error handling and logging for agent processing endpoint in backend/src/main.py
- [ ] T047 [US1] Add CORS middleware configuration in backend/src/main.py
- [ ] T048 [US1] Validate configuration on startup with clear error messages in backend/src/main.py

**Checkpoint**: At this point, User Story 1 should be fully functional - agent can process basic inquiries with database persistence, semantic search, session memory, and observability tracking

---

## Phase 4: User Story 2 - Automated Customer Support Workflow (Priority: P1)

**Goal**: Implement complete customer support workflow with sentiment analysis, customer identification, knowledge retrieval, and channel-specific formatting

**Independent Test**: Send a customer inquiry with contact information, verify sentiment analysis runs, customer identification succeeds with cross-channel matching, conversation is created, knowledge base search returns relevant results, and a properly formatted response is stored as a message with role="agent"

### Implementation for User Story 2

- [ ] T049 [P] [US2] Extract sentiment analysis skill prompt from incubation to backend/src/agent/prompts.py
- [ ] T050 [P] [US2] Extract customer identification skill prompt from incubation to backend/src/agent/prompts.py
- [ ] T051 [P] [US2] Extract knowledge retrieval skill prompt from incubation to backend/src/agent/prompts.py
- [ ] T052 [P] [US2] Extract escalation decision skill prompt from incubation to backend/src/agent/prompts.py
- [ ] T053 [P] [US2] Extract channel adaptation skill prompt from incubation to backend/src/agent/prompts.py
- [ ] T054 [P] [US2] Implement identify_customer @function_tool with CustomerIdentifier cross-channel lookup in backend/src/agent/tools/identify_customer.py
- [ ] T055 [P] [US2] Implement search_knowledge_base @function_tool with pgvector similarity search in backend/src/agent/tools/search_knowledge_base.py
- [ ] T056 [US2] Implement create_ticket @function_tool with conversation creation and linking in backend/src/agent/tools/create_ticket.py
- [ ] T057 [US2] Implement get_customer_history @function_tool with conversation and message retrieval in backend/src/agent/tools/get_customer_history.py
- [ ] T058 [US2] Implement send_response @function_tool that stores message with role="agent" and observability fields in backend/src/agent/tools/send_response.py
- [ ] T059 [US2] Create channel-specific formatters (Gmail, WhatsApp, Web Form, API) in backend/src/agent/formatters.py
- [ ] T060 [US2] Register all 6 tools with Customer Success Agent in backend/src/agent/customer_success_agent.py
- [ ] T061 [US2] Update agent instructions to include complete workflow (sentiment → identification → knowledge → escalation → response) in backend/src/agent/customer_success_agent.py
- [ ] T062 [US2] Add context updates in all tools to track workflow state and conversation_id in backend/src/agent/tools/

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - complete automated customer support workflow is functional with cross-channel customer unification

---

## Phase 5: User Story 3 - Escalation Management (Priority: P2)

**Goal**: Implement intelligent escalation routing based on sentiment trends, conversation context, and business-specific triggers

**Independent Test**: Send inquiries that trigger escalation criteria (negative sentiment, explicit escalation requests, high-value accounts), verify conversation.escalated_to field is updated with correct priority, and confirm escalation status is tracked in conversation.status

### Implementation for User Story 3

- [ ] T063 [US3] Implement escalate_to_human @function_tool that updates conversation.escalated_to and conversation.status in backend/src/agent/tools/escalate_to_human.py
- [ ] T064 [US3] Add sentiment trend analysis logic in escalate_to_human tool in backend/src/agent/tools/escalate_to_human.py
- [ ] T065 [US3] Add conversation looping detection in escalate_to_human tool in backend/src/agent/tools/escalate_to_human.py
- [ ] T066 [US3] Add explicit escalation request detection in escalate_to_human tool in backend/src/agent/tools/escalate_to_human.py
- [ ] T067 [US3] Add high-value account prioritization in escalate_to_human tool in backend/src/agent/tools/escalate_to_human.py
- [ ] T068 [US3] Register escalate_to_human tool with Customer Success Agent in backend/src/agent/customer_success_agent.py
- [ ] T069 [US3] Update agent instructions to include escalation decision-making in backend/src/agent/customer_success_agent.py
- [ ] T070 [US3] Add escalation_triggered and escalation_reason to ProcessInquiryResponse in backend/src/main.py

**Checkpoint**: All core user stories (US1, US2, US3) should now be independently functional with complete escalation management tracked in conversations

---

## Phase 6: User Story 4 - System Testing and Maintenance (Priority: P2)

**Goal**: Implement comprehensive test coverage with unit and integration tests, and clear configuration management for reliable system maintenance

**Independent Test**: Run the test suite, verify all core functionality tests pass including conversation lifecycle, cross-channel customer matching, session persistence, and observability tracking, check test coverage metrics exceed 70%, and confirm configuration can be updated via environment variables without code changes

### Implementation for User Story 4

#### Test Infrastructure
- [ ] T071 [P] [US4] Create pytest configuration in backend/pytest.ini
- [ ] T072 [P] [US4] Create pytest fixtures for database session in backend/tests/conftest.py
- [ ] T073 [P] [US4] Create pytest fixtures for test data (customers, customer_identifiers, conversations, tickets, messages) in backend/tests/conftest.py
- [ ] T074 [P] [US4] Create unit test directory structure in backend/tests/unit/
- [ ] T075 [P] [US4] Create integration test directory structure in backend/tests/integration/

#### Unit Tests (Fast, Mocked Dependencies)
- [ ] T076 [P] [US4] Implement unit tests for identify_customer tool with mocked CustomerIdentifier lookup in backend/tests/unit/test_tools.py
- [ ] T077 [P] [US4] Implement unit tests for search_knowledge_base tool with mocked vector search in backend/tests/unit/test_tools.py
- [ ] T078 [P] [US4] Implement unit tests for create_ticket tool with mocked conversation creation in backend/tests/unit/test_tools.py
- [ ] T079 [P] [US4] Implement unit tests for escalate_to_human tool with mocked conversation updates in backend/tests/unit/test_tools.py
- [ ] T080 [P] [US4] Implement unit tests for send_response tool with mocked message storage in backend/tests/unit/test_tools.py
- [ ] T081 [P] [US4] Implement unit tests for session transformations (Message ↔ EasyInputMessageParam) in backend/tests/unit/test_session_logic.py
- [ ] T082 [P] [US4] Implement unit tests for RunHooks callbacks with mocked context in backend/tests/unit/test_hooks_logic.py
- [ ] T083 [P] [US4] Implement unit tests for channel formatters (Gmail, WhatsApp, Web Form, API) in backend/tests/unit/test_formatters.py
- [ ] T084 [P] [US4] Implement unit tests for prompt template rendering in backend/tests/unit/test_prompts.py

#### Integration Tests (Real Database)
- [ ] T085 [P] [US4] Implement integration tests for Customer CRUD operations in backend/tests/integration/test_database_crud.py
- [ ] T086 [P] [US4] Implement integration tests for CustomerIdentifier CRUD with cross-channel lookup in backend/tests/integration/test_database_crud.py
- [ ] T087 [P] [US4] Implement integration tests for Conversation CRUD with lifecycle tracking in backend/tests/integration/test_database_crud.py
- [ ] T088 [P] [US4] Implement integration tests for Message CRUD with conversation history in backend/tests/integration/test_database_crud.py
- [ ] T089 [P] [US4] Implement integration tests for Ticket CRUD with conversation linking in backend/tests/integration/test_database_crud.py
- [ ] T090 [P] [US4] Implement integration tests for KnowledgeBase CRUD with vector search in backend/tests/integration/test_database_crud.py
- [ ] T091 [P] [US4] Implement integration tests for custom session persistence (get_items, add_items, pop_item) in backend/tests/integration/test_session_persistence.py
- [ ] T092 [P] [US4] Implement integration tests for full agent workflow with real database in backend/tests/integration/test_agent_workflow.py
- [ ] T093 [P] [US4] Implement integration tests for GET /health endpoint in backend/tests/integration/test_api_endpoints.py
- [ ] T094 [P] [US4] Implement integration tests for POST /agent/process endpoint in backend/tests/integration/test_api_endpoints.py
- [ ] T095 [P] [US4] Implement integration tests for GET /agent/history/{conversation_id} endpoint in backend/tests/integration/test_api_endpoints.py
- [ ] T096 [P] [US4] Implement integration tests for knowledge base migration script in backend/tests/integration/test_knowledge_migration.py

#### Test Execution & Coverage
- [ ] T097 [US4] Run pytest unit tests and verify all pass
- [ ] T098 [US4] Run pytest integration tests with real database and verify all pass
- [ ] T099 [US4] Run pytest with coverage report and verify >70% coverage
- [ ] T100 [US4] Implement GET /agent/history/{conversation_id} endpoint in backend/src/main.py

**Checkpoint**: All user stories should now be independently functional with comprehensive test coverage including conversation lifecycle, cross-channel customer unification, session persistence, and observability tracking

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final validation

- [ ] T101 [P] Update README.md with setup instructions from quickstart.md in backend/README.md
- [ ] T102 [P] Add docstrings to all agent tools in backend/src/agent/tools/
- [ ] T103 [P] Add logging for all database operations in backend/src/database/queries.py
- [ ] T104 [P] Add logging for all agent tool executions with observability tracking in backend/src/agent/tools/
- [ ] T105 Validate all environment variables are documented in .env.example in backend/.env.example
- [ ] T106 Run quickstart.md validation end-to-end
- [ ] T107 Verify 100% feature parity with incubation MVP (all 5 skills, all 6 tools, all escalation rules)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (P1) can start after Foundational - No dependencies on other stories
  - US2 (P1) depends on US1 completion (needs agent and database setup)
  - US3 (P2) depends on US2 completion (needs all tools implemented)
  - US4 (P2) can start after US1 completion (tests can be written alongside US2/US3)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - Delivers MVP with basic agent functionality
- **User Story 2 (P1)**: Depends on US1 - Adds complete workflow with all 6 tools and cross-channel customer unification
- **User Story 3 (P2)**: Depends on US2 - Adds escalation management tracked in conversation lifecycle
- **User Story 4 (P2)**: Can start after US1 - Tests can be written in parallel with US2/US3 implementation

### Within Each User Story

**US1 (Production-Ready Agent Deployment)**:
1. Knowledge base migration (T035-T036)
2. Context model and FastAPI setup (T037-T039) - can run in parallel
3. Basic agent setup (T040)
4. Agent processing endpoint (T041-T046)

**US2 (Automated Customer Support Workflow)**:
1. Extract all 5 skill prompts (T049-T053) - can run in parallel
2. Implement P0 tools (T054-T055) - can run in parallel
3. Implement P1 tools (T056-T058) - sequential after P0
4. Channel formatters (T059)
5. Register tools and update instructions (T060-T062)

**US3 (Escalation Management)**:
1. Implement escalate_to_human tool (T063-T067)
2. Register tool and update instructions (T068-T070)

**US4 (System Testing and Maintenance)**:
1. Test infrastructure setup (T071-T075) - can run in parallel
2. All test implementations (T076-T084) - can run in parallel
3. Coverage validation (T097-T099)
4. History endpoint (T100)

### Parallel Opportunities

- **Phase 1**: All 3 tasks can run in parallel (T001-T003)
- **Phase 2**: Models (T006-T012), CRUD operations (T020-T027) can run in parallel within their groups
- **US1**: Context model + FastAPI setup (T039-T041) can run in parallel
- **US2**: Skill prompts (T049-T053), P0 tools (T054-T055) can run in parallel
- **US4**: All test files (T076-T096) can run in parallel

---

## Parallel Example: User Story 2 (Automated Workflow)

```bash
# Launch all skill prompt extractions together:
Task T049: "Extract sentiment analysis skill prompt"
Task T050: "Extract customer identification skill prompt"
Task T051: "Extract knowledge retrieval skill prompt"
Task T052: "Extract escalation decision skill prompt"
Task T053: "Extract channel adaptation skill prompt"

# Launch all P0 tools together:
Task T054: "Implement identify_customer @function_tool with cross-channel lookup"
Task T055: "Implement search_knowledge_base @function_tool"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T036) - CRITICAL
3. Complete Phase 3: User Story 1 (T037-T048)
4. **STOP and VALIDATE**: Test US1 independently with quickstart.md
5. Deploy/demo basic agent with database and semantic search

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (T001-T036)
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!) (T037-T048)
3. Add User Story 2 → Test independently → Deploy/Demo (Complete workflow with cross-channel unification) (T049-T062)
4. Add User Story 3 → Test independently → Deploy/Demo (With escalation tracking) (T063-T070)
5. Add User Story 4 → Test coverage validation (T071-T100)
6. Polish → Final validation (T101-T107)

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T036)
2. Once Foundational is done:
   - Developer A: User Story 1 (T037-T048)
   - Developer B: Start extracting skill prompts for US2 (T049-T053)
3. After US1 complete:
   - Developer A: User Story 2 tools (T054-T062)
   - Developer B: User Story 4 test infrastructure (T071-T075)
4. After US2 complete:
   - Developer A: User Story 3 (T063-T070)
   - Developer B: User Story 4 tests (T076-T100)
5. Both: Polish (T101-T107)

---

## Success Criteria Mapping

Each task contributes to specific success criteria from spec.md:

- **SC-001** (Agent processing <5s): T042-T048, T054-T062
- **SC-002** (Database migrations): T017-T019
- **SC-003** (Semantic search >80% accuracy): T037-T038, T055
- **SC-004** (All 6 tools execute): T054-T058, T063
- **SC-005** (>70% test coverage): T071-T099
- **SC-006** (Concurrent requests): T013-T014
- **SC-007** (100% feature parity): T049-T053, T107
- **SC-008** (Configuration via env vars): T002-T003
- **SC-009** (Health check <100ms): T041
- **SC-010** (Agent processing endpoint): T043-T048

---

## Schema Changes Summary

**New Tables Added**:
- CustomerIdentifier (cross-channel customer matching)
- Conversation (conversation lifecycle tracking)
- ChannelConfig (multi-channel configuration)
- AgentMetric (performance observability)

**Tables Removed**:
- Escalation (replaced by conversation.escalated_to field)
- Response (replaced by messages with role="agent")

**Key Field Changes**:
- All tables now use UUID primary keys
- Messages reference conversation_id (not ticket_id)
- Messages include observability fields: role, tokens_used, latency_ms, tool_calls, channel_message_id
- Tickets reference conversation_id and include category, resolved_at, resolution_notes
- Customers include name field, phone is not unique
- All tables have updated_at field

**Tool Count Change**: 7 tools → 6 tools (send_response replaces separate response table, escalate_to_human updates conversation fields)

---

## Notes

- [P] tasks = different files, no dependencies within the same phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Tests are implemented in US4 rather than TDD approach (not explicitly requested in spec)
- All 5 skill prompts must be preserved exactly from incubation (FR-019)
- All 6 tools must maintain identical behavior to incubation with schema updates (FR-020)
- Knowledge base migration is one-time setup (per user clarification)
- Database CI/CD strategy uses Neon branching (per plan.md)
- Cross-channel customer unification via CustomerIdentifier table enables same customer across email/phone/WhatsApp
- Conversation lifecycle tracking enables better analytics and escalation management
- Observability fields in messages enable cost tracking and performance monitoring
