---
id: 0025
title: Add Comprehensive Integration Test Assertions
stage: green
date: 2026-03-01
surface: agent
model: claude-sonnet-4-6
feature: 005-custom-agent-transition
branch: 005-custom-agent-transition
user: wsl-user
command: continue
labels: ["testing", "integration-tests", "assertions", "quality"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - tests/integration/test_agent_workflow.py
tests:
  - tests/integration/test_agent_workflow.py::TestAgentWorkflowIntegration (6/6 passed)
---

## Prompt

like the multiple strict tests in test_complete_customer_support_workflow function, add more tests in other fcuntions of TestAgentWorkflowIntegration class

can also verify by reading database, context

## Response snapshot

Enhanced all 5 remaining integration test functions with comprehensive assertions similar to test_complete_customer_support_workflow. Each test now verifies:

**1. test_escalation_workflow**
- Tool calls: identify_customer (no args), escalate_to_human
- Tool outputs: confirmation messages with expected content
- Context state: escalation_triggered=True, escalation_reason set, customer_id set
- Database state: conversation.status=ESCALATED, escalated_to field contains support email
- Validates explicit escalation request detection ("speak to a manager")

**2. test_ticket_creation_workflow**
- Tool calls: identify_customer (no args), create_ticket with billing category
- Tool outputs: ticket creation confirmation
- Context state: ticket_id set, customer_id set
- Database state: ticket exists, linked to conversation/customer, category="billing"
- Message persistence: user and agent messages stored
- Validates ticket creation request detection

**3. test_customer_history_workflow**
- Tool calls: identify_customer (no args), get_customer_history
- Tool outputs: history contains previous conversations and billing issue
- Context state: conversation_history populated, customer_id set
- Database state: messages stored in current conversation with correct roles
- Final response: references previous billing issue
- Validates history retrieval across multiple conversations

**4. test_cross_channel_customer_unification**
- Tool calls: identify_customer called for both email and WhatsApp channels
- Tool outputs: customer identification confirmed for both channels
- Context state: same customer_id across both channels (CRITICAL unification test)
- Database state: both conversations linked to same customer
- Message persistence: messages stored for both conversations
- Validates cross-channel customer unification (email → phone lookup)

**5. test_context_state_management**
- Tool calls: identify_customer (no args)
- Tool outputs: customer identification confirmed
- Context state: customer_id/email set, conversation_id maintained, channel unchanged
- Context state: optional fields remain as initialized (ticket_id=None, escalation_triggered=False)
- Context state: db_session maintained throughout execution
- Database state: messages stored, conversation remains active
- Validates context state integrity throughout agent execution

**Common Assertion Pattern Applied to All Tests:**
```python
# 1. Extract tool calls and outputs from result
tool_calls = []
tool_outputs = []
for item in result.new_items:
    raw_item = item.raw_item
    if isinstance(raw_item, ResponseFunctionToolCall):
        tool_calls.append({"name": raw_item.name, "arguments": raw_item.arguments, "call_id": raw_item.call_id})
    elif isinstance(raw_item, dict) and raw_item.get("type", '') == "function_call_output":
        tool_outputs.append({"call_id": raw_item.get("call_id"), "output": raw_item.get("output")})

# 2. Verify tool calls with specific arguments
identify_call = next((tc for tc in tool_calls if tc["name"] == "identify_customer"), None)
assert identify_call is not None
assert identify_call["arguments"] == "{}"

# 3. Verify tool outputs contain expected content
identify_output = next((to for to in tool_outputs if ...), None)
assert identify_output is not None
assert "Customer identified" in identify_output["output"]

# 4. Verify context state changes
assert context.customer_id == str(test_customer.id)
assert context.customer_email == test_customer.email

# 5. Verify database state
await db_session.commit()
updated_conv = await get_conversation(db_session, conversation.id)
assert updated_conv.status == expected_status
```

**Test Results:**
- ✅ test_complete_customer_support_workflow - PASSED
- ✅ test_escalation_workflow - PASSED
- ✅ test_ticket_creation_workflow - PASSED
- ✅ test_customer_history_workflow - PASSED
- ✅ test_cross_channel_customer_unification - PASSED
- ✅ test_context_state_management - PASSED
- ⏭️ test_error_handling_in_workflow - SKIPPED (intentionally)

All 6 active integration tests passing (100% success rate)

## Outcome

- ✅ Impact: Significantly improved test robustness and regression detection. Tests now verify tool calls, arguments, outputs, context state, and database state comprehensively.
- 🧪 Tests: 6/6 integration tests passing with comprehensive assertions (100% success rate)
- 📁 Files: Modified 1 file (test_agent_workflow.py) with ~200 lines of new assertions
- 🔁 Next prompts: Consider running full test suite (unit + integration), or move to next feature task
- 🧠 Reflection: Comprehensive assertions catch more bugs and provide better debugging information when tests fail. Each test now validates the complete workflow from tool calls through database persistence.

## Evaluation notes (flywheel)

- Failure modes observed:
  1. Tests without comprehensive assertions can pass even when tools aren't called correctly
  2. Context state changes can be missed without explicit verification
  3. Database state can diverge from context without validation
  4. Tool outputs can be incorrect without content verification

- Graders run and results (PASS/FAIL):
  - Integration tests: PASS (6/6 active tests)
  - Tool call verification: PASS (all tools called with correct arguments)
  - Context state verification: PASS (all state changes validated)
  - Database state verification: PASS (all database changes validated)
  - Cross-channel unification: PASS (same customer identified across channels)

- Prompt variant (if applicable): N/A

- Next experiment (smallest change to try):
  1. Run full test suite (unit + integration) to ensure no regressions
  2. Consider adding negative test cases (e.g., invalid inputs, missing data)
  3. Consider adding performance assertions (e.g., response time limits)
  4. Consider adding security test cases (e.g., verify tools cannot access other customers' data)
