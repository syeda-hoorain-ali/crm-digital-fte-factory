---
id: 0021
title: Add Kafka verification to E2E tests
stage: green
date: 2026-03-15
surface: agent
model: qwen3-code-plus
feature: 006-channel-integrations
branch: 006-channel-integrations
user: d
command: continue
labels: ["testing", "kafka", "e2e", "verification"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - backend/tests/e2e/test_gmail_real_flow.py
  - backend/tests/e2e/test_whatsapp_real_flow.py
tests:
  - test_gmail_inbound_email_processing (PASSED)
  - test_gmail_reply_threading (PASSED)
  - test_whatsapp_inbound_message_processing (PASSED)
  - test_whatsapp_conversation_continuity (PASSED)
  - test_whatsapp_escalation_detection (PASSED)
---

## Prompt

User asked to add Kafka verification to E2E tests. Started with Gmail tests, then added to WhatsApp tests. User requested to run both test suites together to verify everything passes before committing.

Initial request: "yes i also wnat kafa in it, first add it in gmail tests"
Follow-up: "run both gmail and whatsapp tests one more time"

## Response snapshot

Added Kafka verification to all E2E tests (Gmail and WhatsApp):

**Gmail Tests (2):**
- Added kafka_consumer fixture parameter
- Poll Kafka after webhook processing
- Verify ChannelMessage schema validation
- Check key fields: channel, message_type, customer_id, body

**WhatsApp Tests (3):**
- Added kafka_consumer fixture parameter
- Poll Kafka after webhook processing
- Verify ChannelMessage schema validation
- Verify escalation metadata in Kafka messages
- Fixed Unicode emoji issues for Windows console

**Key Implementation:**
- Poll Kafka consumer with 30-second timeout
- Search for test message by unique test ID
- Validate against ChannelMessage schema
- Verify channel-specific fields and metadata
- Handle cases where subsequent messages aren't sent to Kafka (by design)

**Test Results:**
All 5 E2E tests passing with full webhook → database → Kafka coverage.

## Outcome

- ✅ Impact: E2E tests now verify complete message flow including Kafka delivery
- 🧪 Tests: 5/5 E2E tests passing (2 Gmail, 3 WhatsApp)
- 📁 Files: Modified 2 test files with Kafka verification
- 🔁 Next prompts: Commit and push changes
- 🧠 Reflection: Kafka verification confirms messages are published correctly for NEW conversations only

## Evaluation notes (flywheel)

- Failure modes observed: Unicode emoji encoding errors on Windows console (fixed by replacing with plain text)
- Graders run and results (PASS/FAIL): All tests PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Consider adding Kafka verification to other test suites if needed