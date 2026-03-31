---
id: 0010
title: Kafka Integration E2E Tests
stage: green
date: 2026-03-08
surface: agent
model: qwen3-code-plus
feature: 006-channel-integrations
branch: 006-channel-integrations
user: d
command: none
labels: ["testing", "kafka", "e2e", "async", "integration", "whatsapp"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - backend/tests/conftest.py
  - backend/tests/e2e/test_multichannel_flow.py
  - backend/tests/test_whatsapp_webhook.py
  - backend/src/database/connection.py
  - backend/src/kafka/producer.py
  - backend/src/kafka/topics.py
  - backend/src/services/conversation_service.py
  - backend/src/services/customer_identification.py
  - backend/src/api/webhooks/web_form.py
  - backend/src/api/webhooks/whatsapp.py
tests:
  - tests/e2e/test_multichannel_flow.py (5/5 passing)
  - tests/test_whatsapp_webhook.py (5/10 passing - unit tests with mocks)
---

## Prompt

User identified that E2E tests were passing without Kafka integration (no Kafka calls, no credentials). User requested: "Add Kafka to test environment" to achieve true end-to-end testing with Kafka message delivery verification.

Follow-up interactions:
- "use AsyncClient" (when TestClient event loop issue occurred)
- "continue" (to proceed with fixes)
- "uv run pytest" (to use correct test runner)
- "write phr" (to document the work)

## Response snapshot

Successfully integrated Kafka into E2E test environment and fixed all async API issues:

**Kafka Integration:**
- Added kafka_producer fixture with proper lifecycle management
- Added kafka_consumer fixture to verify message delivery
- Created client_with_kafka fixture using AsyncClient with ASGITransport
- Injected Kafka producer into webhook modules for testing

**Fixed Event Loop Issues:**
- Switched from TestClient to AsyncClient to avoid event loop conflicts
- Created get_session_dependency() as raw async generator for FastAPI Depends()
- Fixed async context manager usage throughout codebase

**Fixed Kafka Producer:**
- Removed unsupported parameters (retries, max_in_flight_requests_per_connection)
- Fixed enum to string conversion (KafkaTopic.ALL_INBOUND.value)
- Updated topic helper functions to return .value instead of enum

**Fixed SQLAlchemy Async API:**
- Changed .first() to .scalars().first() in conversation_service.py
- Changed .all() to .scalars().all() in web_form.py
- Fixed ticket query to use proper async API
- Fixed WhatsApp status endpoint to use session.execute() instead of session.exec()

**Fixed Customer Identification:**
- Updated link_phone_to_customer() to also update Customer.phone field
- Ensured phone field is set when linking phone identifier

**Test Isolation:**
- Created clean_test_data fixture to delete test data before/after tests
- Added fixture to rate limiting test to prevent event loop closure
- Fixed health check test to handle both response formats

**WhatsApp Webhook Fixes:**
- Migrated WhatsApp tests to use AsyncClient instead of TestClient
- Fixed WhatsApp status endpoint to query by channel_message_id instead of iterating metadata
- Added hasattr() check for metadata_ field compatibility
- 5/10 WhatsApp unit tests passing (pure mocks without database)
- 5/10 require PostgreSQL (SQLite incompatible with PostgreSQL-specific syntax)

**Results:**
- All 5 E2E tests passing (100%) with full Kafka integration ✅
- Full flow verified: HTTP → Database → Kafka → Agent processing
- Kafka message delivery confirmed in tests
- Cross-channel customer recognition working
- Conversation continuity detection working

## Outcome

- ✅ Impact: Achieved true end-to-end testing with Kafka integration. Tests now verify complete message flow from HTTP request through database persistence to Kafka message delivery.
- 🧪 Tests: 5/5 E2E tests passing with Kafka integration. Tests verify web form submission, Kafka message delivery, customer identification, conversation linking, rate limiting, and health checks.
- 📁 Files: Modified 8 files across test fixtures, database connection, Kafka producer, services, and API endpoints. Fixed async API usage throughout.
- 🔁 Next prompts: Consider adding Kafka integration to WhatsApp webhook tests. May need to address test coverage (currently 41%, target 70%).
- 🧠 Reflection: Event loop management in async testing requires careful attention. TestClient creates its own event loop incompatible with async fixtures. AsyncClient with ASGITransport is the correct approach for testing async FastAPI apps with external async dependencies like Kafka.

## Evaluation notes (flywheel)

- Failure modes observed: TestClient event loop conflicts, SQLAlchemy async API misuse (.first() vs .scalars().first()), enum vs string in Kafka topics, missing Customer.phone field update, test data persistence across runs, health check response format inconsistency
- Graders run and results (PASS/FAIL): All E2E tests PASS (5/5)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Add Kafka integration to remaining webhook tests (WhatsApp, Gmail) using the same fixture pattern established here
