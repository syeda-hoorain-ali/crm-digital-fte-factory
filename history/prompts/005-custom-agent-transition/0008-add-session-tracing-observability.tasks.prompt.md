---
id: "0008"
title: "Add Session Management and Tracing/Observability Infrastructure"
stage: "tasks"
date: "2026-02-25"
surface: "agent"
model: "claude-sonnet-4-6"
feature: "005-custom-agent-transition"
branch: "005-custom-agent-transition"
user: "wsl-user"
command: "tasks update"
labels: ["session-management", "tracing", "observability", "postgresql", "runhooks"]
links:
  spec: "specs/005-custom-agent-transition/spec.md"
  plan: "specs/005-custom-agent-transition/plan.md"
  tasks: "specs/005-custom-agent-transition/tasks.md"
  data_model: "specs/005-custom-agent-transition/data-model.md"
  api_contract: "specs/005-custom-agent-transition/contracts/api.yaml"
  sdk_reference: "specs/005-custom-agent-transition/openai-agents-sdk-reference.md"
files:
  - "specs/005-custom-agent-transition/spec.md"
  - "specs/005-custom-agent-transition/plan.md"
  - "specs/005-custom-agent-transition/tasks.md"
  - "specs/005-custom-agent-transition/data-model.md"
  - "specs/005-custom-agent-transition/contracts/api.yaml"
  - "specs/005-custom-agent-transition/openai-agents-sdk-reference.md"
tests: []
---

# Prompt

User identified critical missing infrastructure: session management for conversation memory and tracing/hooks for agent metrics collection. User requested:

1. Custom PostgreSQL session implementation (not SQLiteSession) using Message table as storage backend
2. Session operations following SessionABC protocol (get_items, add_items, pop_item, clear_session)
3. EasyInputMessageParam as session item format (4 fields: role, content, phase, type)
4. Transform existing Message fields to/from EasyInputMessageParam without additional storage
5. clear_session() as no-op (pass) to preserve all message data for audit trail
6. RunHooks implementation for lifecycle observability (on_agent_start, on_agent_end, on_tool_start, on_tool_end, on_handoff)
7. trace() context manager with group_id for conversation linking
8. Token usage tracking from result.raw_responses and AgentMetric population
9. Structured JSON logging with timestamps and correlation IDs
10. Reorganize tests into unit/ and integration/ subdirectories

User also ran command to fetch OpenAI Agents SDK documentation:
```bash
gh api repos/panaversity/agentfactory/contents/apps/learn-app/docs/05-Building-Custom-Agents/34-openai-agents-sdk --jq '.[] | {name: .name, path: .path, type: .type, download_url: .download_url, size: .size}'
```

Downloaded and reviewed:
- 06-sessions-conversation-memory.md (SessionABC protocol, SQLiteSession patterns)
- 07-tracing-hooks-observability.md (trace(), RunHooks, token tracking)
- 02-function-tools-context-objects.md (RunContextWrapper, context access)

# Response

## Session Management Implementation

### Custom PostgreSQL Session Design

**Key Decision**: Reuse Message table for dual purpose (business data + session memory) instead of creating separate SessionItem table.

**Rationale**:
- No additional storage needed
- Existing fields (content, role, created_at) provide all session data
- Natural isolation via conversation_id
- Preserves audit trail (clear_session is no-op)

**Implementation Pattern**:
```python
class PostgreSQLSession(SessionABC):
    """Custom PostgreSQL session using Message table."""

    async def get_items(self, limit: int | None = None) -> List[dict]:
        # Query Messages by conversation_id
        # Transform to EasyInputMessageParam:
        #   - content: Message.content
        #   - role: customer→user, agent→assistant, system→system
        #   - phase: agent→"final_answer", user→None
        #   - type: "message"

    async def add_items(self, items: List[dict]) -> None:
        # Transform EasyInputMessageParam to Message:
        #   - Extract content, role from item
        #   - Map SDK role to business role (user→customer, assistant→agent)
        #   - Derive direction from role (user→inbound, assistant→outbound)

    async def pop_item(self) -> dict | None:
        # Delete most recent Message by conversation_id
        # Return as EasyInputMessageParam before deleting

    async def clear_session(self) -> None:
        pass  # No-op to preserve audit trail
```

### EasyInputMessageParam Format

**Structure** (4 fields only):
- `content` (str): Message text
- `role` (Literal["user", "assistant", "system", "developer"]): SDK role
- `phase` (Optional[Literal["commentary", "final_answer"]]): Agent message phase
- `type` (Literal["message"]): Always "message"

**No Additional Storage Required**: Construct from existing Message fields without session_item_data column.

## Tracing and Observability Implementation

### trace() Context Manager

**Purpose**: Group related agent runs into logical workflows, link multi-turn conversations.

**Pattern**:
```python
with trace(
    workflow_name="Customer Support",
    group_id=conversation_id,  # Links all turns
    metadata={"channel": "api", "customer_tier": "premium"}
):
    result = await Runner.run(agent, message, session=session, hooks=hooks)
```

**Key Features**:
- Automatic tracing to OpenAI dashboard (platform.openai.com/traces)
- group_id links multi-turn conversations
- metadata for filtering and analysis

### RunHooks Implementation

**Purpose**: Lifecycle callbacks for metrics collection and structured logging.

**Lifecycle Methods**:
- `on_agent_start`: Log start, track start time
- `on_agent_end`: Calculate latency, extract tokens, populate AgentMetric table
- `on_tool_start`: Log tool invocation
- `on_tool_end`: Log tool completion, track tool call count
- `on_handoff`: Log agent handoffs

**Token Usage Extraction**:
```python
async def on_agent_end(self, context, agent, output):
    # Extract from result.raw_responses
    for response in output.raw_responses:
        if hasattr(response, 'usage') and response.usage:
            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

    # Calculate cost
    estimated_cost = (
        (total_input_tokens / 1_000_000) * INPUT_COST_PER_M +
        (total_output_tokens / 1_000_000) * OUTPUT_COST_PER_M
    )

    # Populate AgentMetric table
    metrics = [
        AgentMetric(metric_name="tokens_used", metric_value=total_tokens, ...),
        AgentMetric(metric_name="latency_ms", metric_value=latency_ms, ...),
        AgentMetric(metric_name="estimated_cost", metric_value=estimated_cost, ...)
    ]
```

**Structured Logging**:
```python
log_entry = {
    "event": "agent_start",
    "agent": agent.name,
    "conversation_id": self.conversation_id,
    "timestamp": datetime.utcnow().isoformat(),
    "correlation_id": self.conversation_id
}
print(json.dumps(log_entry))
```

## Test Organization

### Unit Tests (Fast, Mocked Dependencies)
**Location**: `backend/tests/unit/`

**Files**:
- `test_tools.py`: Tool logic with mocked database
- `test_session_logic.py`: Session transformations (Message ↔ EasyInputMessageParam)
- `test_hooks_logic.py`: Hook callbacks with mocked context
- `test_formatters.py`: Channel formatting logic
- `test_prompts.py`: Prompt template rendering

### Integration Tests (Real Database)
**Location**: `backend/tests/integration/`

**Files**:
- `test_database_crud.py`: Real database operations
- `test_session_persistence.py`: Session operations with real Message table
- `test_agent_workflow.py`: Full agent runs with real database
- `test_api_endpoints.py`: FastAPI endpoints with real database
- `test_knowledge_migration.py`: Knowledge base migration script

**Benefits**:
- Fast feedback loop (run unit tests during development)
- CI/CD optimization (fail fast on unit tests, then run integration)
- Clear separation (mocked vs real infrastructure)

## Artifacts Updated

### 1. spec.md
**Added Functional Requirements**:
- FR-030: Custom PostgreSQL session following SessionABC protocol
- FR-031: Async session operations (get_items, add_items, pop_item, clear_session)
- FR-032: Session isolation by conversation_id
- FR-033: Transform Message ↔ EasyInputMessageParam (role mapping, phase derivation)
- FR-034: Transform EasyInputMessageParam → Message (extract content/role, derive business role)
- FR-035: clear_session() as no-op to preserve audit trail
- FR-036: RunHooks with lifecycle methods
- FR-037: trace() context manager with workflow_name and group_id
- FR-038: Link multi-turn conversations using group_id
- FR-039: Track token usage from result.raw_responses
- FR-040: custom_span() for sub-operations
- FR-041: Structured JSON logging with timestamps and correlation IDs
- FR-042: Populate AgentMetric table via RunHooks

### 2. data-model.md
**Updated Message Entity**:
- Added session implementation notes
- Documented dual purpose (business data + session memory)
- Documented session operations mapping to Message CRUD
- Documented role mapping (customer→user, agent→assistant)
- Documented phase derivation (agent→"final_answer", user→None)
- Documented clear_session() as no-op

### 3. plan.md
**Added Research Questions**:
- Custom Session Implementation
- Tracing and Hooks
- Token Usage Tracking

**Added Technology Decisions**:
- Session Backend: Custom PostgreSQL using Message table
- Session Item Format: EasyInputMessageParam
- Session Isolation: conversation_id as session_id
- Tracing Strategy: OpenAI Agents SDK trace() + RunHooks
- Observability Hooks: Custom RunHooks implementation
- Token Tracking: Extract from result.raw_responses

**Updated Project Structure**:
- Added `backend/src/agent/session.py` (custom PostgreSQL session)
- Added `backend/src/agent/hooks.py` (RunHooks for observability)
- Added `backend/tests/unit/` directory
- Added `backend/tests/integration/` directory
- Added `test_session.py` and `test_hooks.py`

### 4. tasks.md
**Added Phase 2 Tasks** (T026-T034):
- T026: Implement custom PostgreSQL session class
- T027: Implement get_items() with Message → EasyInputMessageParam transformation
- T028: Implement add_items() with EasyInputMessageParam → Message transformation
- T029: Implement pop_item() to delete most recent Message
- T030: Implement clear_session() as no-op
- T031: Implement RunHooks class with lifecycle methods
- T032: Add structured JSON logging in RunHooks
- T033: Add token usage extraction in RunHooks.on_agent_end
- T034: Add AgentMetric population in RunHooks.on_agent_end

**Renumbered All Subsequent Tasks**: T035-T107 (was T026-T086)

**Updated Phase 3 Tasks**:
- T042: Integrate agent execution with Runner.run() using custom session and hooks
- T043: Wrap agent runs in trace() context manager with group_id

**Reorganized Phase 6 Tests** (T070-T100):
- Created unit test tasks (T075-T084) with mocked dependencies
- Created integration test tasks (T085-T096) with real database
- Separated test execution (T097: unit, T098: integration, T099: coverage)

### 5. openai-agents-sdk-reference.md
**Added Section 8**: Custom Session Implementation with PostgreSQL
- Complete PostgreSQLSession class implementation
- get_items() with role mapping and phase derivation
- add_items() with reverse transformation
- pop_item() with delete and return
- clear_session() as no-op
- Usage pattern with Runner.run()

**Added Section 9**: Tracing and Observability with RunHooks
- trace() context manager pattern
- Complete ObservabilityHooks class implementation
- on_agent_start: logging and timing
- on_agent_end: latency, tokens, cost calculation, AgentMetric population
- on_tool_start/end: tool call tracking
- on_handoff: agent handoff logging
- Complete usage pattern with session + hooks + trace

### 6. contracts/api.yaml
**Updated ProcessInquiryResponse**:
- Added `observability` object with:
  - `tokens_used`: Total tokens consumed
  - `latency_ms`: Processing latency
  - `tool_calls`: List of tools called
  - `trace_id`: OpenAI trace ID for debugging
- Updated conversation_id description to mention session_id role

## Implementation Impact

**New Files Required**:
- `backend/src/agent/session.py` (PostgreSQLSession class)
- `backend/src/agent/hooks.py` (ObservabilityHooks class)
- `backend/tests/unit/test_session_logic.py`
- `backend/tests/unit/test_hooks_logic.py`
- `backend/tests/integration/test_session_persistence.py`

**Modified Files**:
- `backend/src/main.py`: Integrate session and hooks with Runner.run(), wrap in trace()
- `backend/src/agent/customer_success_agent.py`: Pass session and hooks to Runner
- All tool files: Access context for conversation_id

**Database Schema**: No changes needed (Message table already has all required fields)

**Test Count**: +10 tasks (5 unit, 5 integration) for session and hooks testing

## Key Architectural Decisions

1. **Reuse Message Table**: No separate SessionItem table, dual-purpose design
2. **No Additional Storage**: Construct EasyInputMessageParam from existing fields
3. **clear_session() No-Op**: Preserve audit trail, create new conversation for fresh start
4. **conversation_id as session_id**: Natural isolation boundary
5. **RunHooks for Metrics**: Populate AgentMetric table via lifecycle callbacks
6. **trace() for Linking**: group_id links multi-turn conversations in OpenAI dashboard
7. **Unit/Integration Split**: Fast feedback loop with clear separation

## Validation Checklist

- [x] All functional requirements added (FR-030 through FR-042)
- [x] Data model updated with session implementation notes
- [x] Plan updated with research questions and technology decisions
- [x] Tasks updated with session/hooks implementation (T026-T034)
- [x] All subsequent tasks renumbered (T035-T107)
- [x] Tests reorganized into unit/ and integration/ subdirectories
- [x] OpenAI Agents SDK reference updated with comprehensive examples
- [x] API contract updated with observability metadata
- [x] No database schema changes required (reusing Message table)
- [x] clear_session() documented as no-op for audit trail preservation

## Next Steps

1. Implement PostgreSQLSession class (T026-T030)
2. Implement ObservabilityHooks class (T031-T034)
3. Integrate session and hooks with agent execution (T042-T043)
4. Write unit tests for session transformations (T081)
5. Write unit tests for hooks callbacks (T082)
6. Write integration tests for session persistence (T091)
7. Verify observability metadata in API responses
8. Validate trace linking in OpenAI dashboard

## Outcome

All artifacts updated with comprehensive session management and tracing/observability infrastructure. Custom PostgreSQL session implementation reuses Message table for dual purpose (business data + session memory) without additional storage. RunHooks implementation provides lifecycle callbacks for AgentMetric population and structured logging. Tests reorganized into unit/ and integration/ subdirectories for fast feedback loop and clear separation.

Total task count: 107 tasks (was 86, added 10 for session/hooks, renumbered all subsequent tasks +11).
