---
id: 0026
title: fix-database-persistence-content-tool-calls
stage: green
date: 2026-03-02
surface: agent
model: claude-sonnet-4-6
feature: 005-custom-agent-transition
branch: 005-custom-agent-transition
user: Afroz
command: interactive
labels: ["database", "persistence", "tool-calls", "content-extraction", "customer-identification"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - backend/src/agent/session.py
  - backend/src/database/queries/customer.py
  - backend/src/database/queries/__init__.py
  - backend/src/main.py
tests:
  - Manual API testing with Neon database
  - Verified tool_calls storage in messages table
  - Verified content extraction from SDK format
  - Verified customer identification before conversation creation
---

## Prompt

User reported three critical database persistence issues after testing the agent:

1. **Content storing raw SDK format**: Messages table was storing `[{'annotations': [], 'text': "I'm sorry...", 'type': 'output_text', 'logprobs': []}]` instead of clean text like `"I'm sorry, I couldn't find any relevant articles..."`

2. **tool_calls always empty**: Even though agent was calling tools (agent_metrics showed tool_call_count=2), the messages.tool_calls field was always `[]`

3. **Customer ID constraint violation**: API was failing with `null value in column "customer_id" of relation "conversations" violates not-null constraint` because conversation was being created BEFORE identifying/creating the customer

User also questioned why messages table has tokens_used, latency_ms, sentiment_score fields when agent_metrics table already tracks these.

User provided example of tool call format from logs:
```
ResponseFunctionToolCall(arguments='{"query":"refund policy"}', call_id='function-call-3550590795610739579', name='search_knowledge_base', type='function_call', id='__fake_id__', status=None, provider_data={'model': 'gemini-2.5-flash', 'response_id': 'GoWlaaPAGLDWvdIPkeKJ4AU'})
{'call_id': 'function-call-3550590795610739579', 'output': 'No relevant articles found in knowledge base. This may require human assistance.', 'type': 'function_call_output'}
ResponseOutputMessage(id='__fake_id__', content=[ResponseOutputText(annotations=[], text="I can't find any information about the refund policy in our knowledge base. Would you like me to escalate this to a human agent who can provide you with more details?", type='output_text', logprobs=[])], role='assistant', status='completed', type='message', phase=None, provider_data={'model': 'gemini-2.5-flash', 'response_id': '5YWlaaWNL4uikdUPi76vwAs'})
```

User wanted to store items in correct sequence: `[text, text, tool, text, tool, tool, tool, text]`

## Response snapshot

Fixed all three critical database persistence issues:

### 1. Content Extraction Fix
Added `_extract_text_from_content()` static method to PostgresSession that extracts clean text from SDK content format:
- Handles string content (returns as-is)
- Handles list of dicts (extracts 'text' field from each)
- Handles list of strings (joins with space)
- Handles dict (extracts 'text' or 'content' field)

Modified `add_items()` to call this method before storing content.

### 2. Tool Calls Capture Fix
Completely rewrote `add_items()` method to properly capture tool calls:
- Added `_pending_tool_calls: dict[str, dict]` as instance variable to persist across calls
- Detects `ResponseFunctionToolCall` objects (type="function_call") and stores call_id, name, arguments
- Detects `FunctionCallOutput` objects (type="function_call_output") and stores output, status
- Merges both by call_id into single dict
- Attaches merged tool_calls to the next assistant message
- Converts to list format when storing: `list(tool_calls_to_store.values())`

### 3. Customer Identification Fix
Created `identify_or_create_customer()` function in `src/database/queries/customer.py`:
- Tries to find existing customer by email
- Tries to find existing customer by phone
- If not found, creates new customer with provided contact info
- Creates CustomerIdentifier records for cross-channel matching
- Returns Customer object

Modified `src/main.py` API endpoint to:
- Call `identify_or_create_customer()` FIRST (before conversation creation)
- Pass customer.id to `create_conversation()`
- Use customer email/phone from database (not request) in context

### 4. Redundant Fields Discussion
Explained that messages table fields (tokens_used, latency_ms, sentiment_score) serve different purposes:
- **agent_metrics**: Tracks OVERALL execution (total tokens for entire agent run with multiple tool calls)
- **messages fields**: Would track PER-MESSAGE costs (useful for billing individual messages)

Currently these fields are NULL in messages table - they're not being populated but could be useful for future per-message tracking.

## Outcome

- ✅ Impact: All three critical database persistence issues resolved. Messages now store clean text content, tool_calls are captured and stored correctly, and customer identification happens before conversation creation.
- 🧪 Tests: Manual API testing confirmed tool_calls saving correctly in Neon database. User verified: "i again change the code now it's working, i tested it it is saving the tool_calls in database"
- 📁 Files: Modified 4 files (session.py, customer.py, queries/__init__.py, main.py)
- 🔁 Next prompts: Consider removing unused fields from messages table (tokens_used, latency_ms, sentiment_score) if per-message tracking is not needed
- 🧠 Reflection: The tool_calls capture was complex because SDK sends items in sequence (message, tool_call, tool_output, message) and we needed to merge tool_call + tool_output by call_id before attaching to assistant message. Using a dict keyed by call_id was the right approach.

## Evaluation notes (flywheel)

- Failure modes observed: Initial attempts failed because we were looking for wrong item types (function_call_output instead of function_call), had variable scoping issues (role/content/direction unbound), and didn't understand SDK's item sequence
- Graders run and results (PASS/FAIL): Manual testing PASS - user confirmed tool_calls now saving correctly
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Run full integration test suite to verify all fixes work together, consider schema cleanup for unused message fields
