---
id: 0027
title: Fix integration test failures and implement automatic cleanup
stage: green
date: 2026-03-31
surface: agent
model: qwen3-code-plus
feature: 006-channel-integrations
branch: 006-channel-integrations
user: d
command: pytest tests/integration/
labels: ["testing", "integration-tests", "database-cleanup", "type-safety", "fixtures"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - backend/tests/integration/test_helpers.py
  - backend/tests/integration/conftest.py
  - backend/tests/integration/test_agent_workflow.py
  - backend/tests/integration/test_api_endpoints.py
  - backend/tests/integration/test_database_crud.py
  - backend/tests/integration/test_tools.py
  - backend/src/database/queries/customer.py
  - backend/src/database/queries/ticket.py
tests:
  - tests/integration/test_database_crud.py (6 tests passing)
  - tests/integration/test_api_endpoints.py (all tests passing)
  - tests/integration/test_agent_workflow.py (all tests passing)
  - tests/integration/test_tools.py (all tests passing)
  - tests/integration/test_cross_channel.py (all tests passing)
  - tests/integration/test_customer_identification.py (all tests passing)
  - tests/integration/test_gmail_webhook.py (all tests passing)
  - tests/integration/test_knowledge_migration.py (all tests passing)
  - tests/integration/test_session_persistence.py (all tests passing)
  - tests/integration/test_web_form_endpoints.py (all tests passing)
---

## Prompt

User requested to fix all integration test failures iteratively:

1. "now run the integration tests one by one file, and iterate until all are success"
2. "fix this first" - referring to type error: Argument of type "str | None" cannot be assigned to parameter "identifier_value" of type "str"
3. "isn't write a code in every test function would be too much? what about creating helper function of fixtures"
4. "first using mcp server, clear ALL data from database"
5. Multiple "Continue" requests to proceed with fixes
6. "wait there are some errors, i'll give it one by one" - Cannot access attribute "rowcount" for class "Result[Any]"
7. "first fix this" - fix the rowcount type error
8. "write phr (of all integration tests are passing)"

## Response snapshot

Fixed all integration test failures through systematic debugging:

**Root Causes Identified:**
1. **db_session parameter mismatch**: Tests passing `session=session` to CustomerSuccessContext, but class expects `db_session=session`
2. **Type errors with optional fields**: test_customer.email and test_customer.phone are `str | None` but being passed to functions requiring non-None strings
3. **Database pollution**: Accumulated test data from multiple runs causing unique constraint violations
4. **Cleanup not executing**: Simple yield pattern in async fixtures not triggering cleanup code
5. **Field name mismatch**: `meta_data` parameter vs `metadata_` model field in customer.py
6. **Function signature mismatch**: update_ticket had wrong parameter names (title/description vs category/resolution)
7. **Type checker limitation**: Result.rowcount exists at runtime but not in type hints

**Solutions Implemented:**

1. **Created test_helpers.py** with cleanup functions:
   - `cleanup_customer_data()` - deletes in proper FK order (messages → tickets → conversations → identifiers → customer)
   - `cleanup_conversation_data()` - deletes conversation and related data
   - `cleanup_knowledge_base_entry()` - deletes KB entries
   - `cleanup_customer_identifier()` - deletes identifiers
   - Added logging to track cleanup operations

2. **Modified all fixtures in conftest.py** to use try-finally pattern:
   ```python
   @pytest.fixture
   async def test_customer(session: AsyncSession):
       customer = await create_customer(...)
       await session.commit()
       try:
           yield customer
       finally:
           try:
               await cleanup_customer_data(session, customer.id)
           except Exception as e:
               print(f"Warning: Cleanup failed for customer {customer.id}: {e}")
   ```
   - Updated 8 fixtures: test_customer, test_customer_premium, test_customer_identifier_email, test_customer_identifier_phone, test_conversation, test_message, test_ticket, test_knowledge_article

3. **Fixed type errors** by adding assertions:
   ```python
   assert test_customer.email is not None
   ```
   - Added in 12+ test methods and fixtures across all integration test files

4. **Fixed db_session parameter** in CustomerSuccessContext calls:
   - Changed `session=session` to `db_session=session` in all test files

5. **Fixed database schema issues**:
   - customer.py: Changed `meta_data=meta_data or {}` to `metadata_=meta_data or {}`
   - ticket.py: Updated update_ticket signature to match model fields (category/resolution instead of title/description)

6. **Fixed type checker errors**:
   - Added `# type: ignore[attr-defined]` comments for Result.rowcount access in test_helpers.py

7. **Cleared database** using MCP server to remove accumulated test data (19 rows across 13 tables)

**Verification:**
- All integration tests now passing (exit code 0)
- Cleanup functions executing properly (confirmed via logs showing "Starting cleanup for customer..." and "Deleted N rows")
- Database remains clean after test runs
- Type errors resolved across all test files

## Outcome

- ✅ Impact: All integration tests passing (100% success rate), automatic cleanup preventing database pollution
- 🧪 Tests: 50+ integration tests across 10 test files all passing with proper cleanup
- 📁 Files: Created 1 new file (test_helpers.py), modified 7 files (conftest.py, 4 test files, 2 query files)
- 🔁 Next prompts: Run E2E tests to verify end-to-end flows, consider adding cleanup verification tests
- 🧠 Reflection: Try-finally pattern in async fixtures is critical for reliable cleanup; simple yield pattern doesn't guarantee cleanup execution in pytest-asyncio 1.3.0

## Evaluation notes (flywheel)

- Failure modes observed: Simple yield pattern in async fixtures doesn't execute cleanup code after yield; type narrowing required for optional fields; Result.rowcount not in type hints despite runtime availability
- Graders run and results (PASS/FAIL): All integration tests PASS (exit code 0)
- Prompt variant (if applicable): Systematic debugging approach - identify root cause before fixing, use fixtures for cleanup instead of per-test cleanup
- Next experiment (smallest change to try): Verify E2E tests work with same cleanup pattern, consider adding autouse fixture to verify database is clean before each test
